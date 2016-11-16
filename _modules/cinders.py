#_*_coding:utf8_*_
#!/usr/bin/env python
import urllib2
import json
import os
import salt.client
import logging
import time
import salt.utils
from hashlib import sha1


log = logging.getLogger(__name__)
_service_type='cinderv2'



#参数处理
def validate(local_argv,kwargs):
       if kwargs:extra_fun=set(kwargs)-set(local_argv)
       for k,v in local_argv.items():
            if v == None or v == True or v == False :continue
            local_argv[k]=v.strip()
            if v.strip() == "True" or v.strip() == "true":local_argv[k]=True
            elif v.strip() == "False" or v.strip() == "false":local_argv[k]=False
            elif v.strip() == "" :local_argv[k]=None
       try:
            local_argv["extra_fun"]=list(extra_fun) 
       except Exception,e:
            pass
       return local_argv
   

#打印日志
def print_log(argv):
      log_path='/tmp/volume.log'       
      with salt.utils.fopen(log_path, 'a+') as fp_:
                            for i in argv:
                                 fp_.write("%s:\n%s\n"%(i,argv[i]))

#获取Provider信息
def get_Provider_info(provider_name,driver_name='nova'):
        import yaml
        data={'data':[],'error':[]}
        file_name='%s_%s.conf'%(provider_name,driver_name)
        Provider_dir='/etc/salt/cloud.providers.d/'
        provider_file='%s%s'%(Provider_dir,file_name)
        try:
            pro_info=yaml.load(file(provider_file))
            identity_url,user,password,tenant,=pro_info[provider_name]['identity_url'],pro_info[provider_name]['user'],pro_info[provider_name]['password'],pro_info[provider_name]['tenant']
        except Exception,e:
                   data['error'].append(e)
                   data['error'].append(provider_name)
                   return  data
        else:
                 for i in 'user','password','tenant','identity_url':
                          data['data'].append({i:eval(i)})
                 return data

#按照_service_type查找对应的endport
def get_serviceCatalog(obj_service,service_type):
      data={'publicURL':'','tenan_id':'','error':[]}
      for i in range(len(obj_service)):
          for k  in obj_service[i].keys():
              try:
                   if k == 'name' and  obj_service[i][k] == str(service_type):
                       data['publicURL']= obj_service[i]["endpoints"][0]["publicURL"]
                       #data['tenan_id']=obj_service[i]["endpoints"][0]["id"]
              except Exception,e:
                  data['error'].append(e)
      return  data


#获取token
def get_token(provider_name,service_type,driver_name='nova'):
   data={'data':[],'error':[]}
   _url_keyword='/tokens'
   #username,password,url,tenan_user=Get_Provider_info(provider_name,driver_name)
   result=get_Provider_info(provider_name,driver_name)
   if result['error']:
           return result
   else:
       for i in result['data']:
           for k,v in i.items():
                  globals().update({k:v})
   
   url='%s%s'%(identity_url,_url_keyword)
   params=json.dumps(
          {"auth":{"passwordCredentials":{"username":user, "password":password}, "tenantName":tenant}})
   headers ={"Content-type":"application/json","Accept": "application/json"}
   req = urllib2.Request(url,params,headers)
   respones = urllib2.urlopen(req)
   result=json.loads(respones.read())
   #servicecatlog: {'tenan_id': u'82cbcefb2e7d495596aaffe4cf9feb10', 'publicURL': u'http://10.20.100.3:8776/v2/80b9ec45d67946eea03d476463a8883c'
   data_dic=get_serviceCatalog(result['access']['serviceCatalog'],service_type)
   data_dic['tenan_id']= result['access']['token']['tenant']['id']
   data_dic['auth_token']=result['access']['token']['id']
   #{'auth_token': u'gAAAAABX1jjHZs3lC8Hyl5scYU_uGg8MPfmojHwTolUXGnj5iauArG-MH3subD0D9rLLfl8l2lTmKAf4SZkggdxLm6stw95bP-Ny7kvPbkzlS47RQyUUfh521_zgZuyQIu1cRaLwhZmKoNaLBVeA8bVYf2ir-D0oi3NrH_Cxu_rNRHLfBptC7T0', 'tenan_id': u'80b9ec45d67946eea03d476463a8883c', 'publicURL': u'http://10.20.100.3:8776/v2/80b9ec45d67946eea03d476463a8883c'
   #print  data_dic'''
   return data_dic




#获取云盘列表(自动上报)
def  get_volumes_list(provider_name,
                      driver_name='nova'):
     _url_keyword='/volumes/detail'
     token=get_token(provider_name,_service_type,driver_name)
     if token['error']:
         return json.dumps({'flag':False, 'msg':'error::{0}'.format(token['error'][0])})
     else:
         headers={'X-Auth-Token':token['auth_token']}
         url="%s%s"%(token['publicURL'],_url_keyword)
         data = None
         req = urllib2.Request(url,data,headers)
         respones = urllib2.urlopen(req)
         result=json.loads(respones.read())
     for i in range(len(result['volumes'])):
         result['volumes'][i]["os_vol_host_attr_host"]=result['volumes'][i].pop("os-vol-host-attr:host")
         result['volumes'][i]["os_vol_mig_status_attr_migstat"]=result['volumes'][i].pop("os-vol-mig-status-attr:migstat")
         result['volumes'][i]["os_vol_tenant_attr_tenant_id"]=result['volumes'][i].pop("os-vol-tenant-attr:tenant_id")
         result['volumes'][i]["os_vol_mig_status_attr_name_id"]=result['volumes'][i].pop("os-vol-mig-status-attr:name_id")
         for x,v  in result['volumes'][i].items():
             if x == "bootable":
                 if x:result['volumes'][i][x]=True
                 else:result['volumes'][i][x]=False
     return  result


#获取云盘状态
def get_volume_status(token,
                      volume_url,
                      headers):
        data_result={"status":'',"error":[]}
        i=300
        data=None
        req = urllib2.Request(volume_url,data,headers)
        try:
            while i > 1:                    
                 respones = urllib2.urlopen(req)
                 result=json.loads(respones.read())    
                 if result['volume']["status"] == 'available' or result['volume']["status"]=="error":
                     status=result['volume']["status"]
                     data_result["status"]=status
                     break                              
                 time.sleep(1)
                 i-=1
        except Exception,e:
                data_result["error"].append(e)
                return data_result
        return data_result


#run_volume_async
def  run_volume_async(result,post_url,id_,jid):
     RET = 'create_volume_callback'
     TGT = 'master-minion'
     FUN = 'cmd.run'
     LOCAL = salt.client.LocalClient()
     kwarg={
         "cmd":'date',
         "result":result,
         "post_url":post_url,
         "id":id_,
         "jid":jid,
     }
     ret = LOCAL.cmd(TGT, FUN,ret=RET,jid=jid,kwarg=kwarg)
     return ret

#创建云盘列表
def create_volumes(volume_id,
                   callback,
                   provider_name,
                   jid=None,
                   driver_name='nova',
                   size=1,
                   name=None,
                   description=None,
                   source_volid=None,
                   volume_type=None,
                   availability_zone='nova',
                   imageRef=None,
                   source_replica=None,
                   consistencygroup_id=None,
                   multiattach=False,
                   snapshot_id=None,
                   **kwargs):
     
     local_argv=locals()
     if kwargs:
         kwargs=local_argv.pop("kwargs")["__pub_arg"][0]
     else:kwargs={}
     local_argv=validate(local_argv,kwargs)
     print_log(local_argv)
     try:
          local_argv["extra_fun"]
     except Exception:
            pass
     if not jid:jid=sha1('%s%s' % (os.urandom(16), time.time())).hexdigest()  
     _url_keyword='/volumes'
     params={"volume":{"size":local_argv['size'],"availability_zone": local_argv['availability_zone'],"source_volid":local_argv['source_volid'],"description":local_argv['description'],"multiattach ":local_argv['multiattach'],"snapshot_id": local_argv['snapshot_id'],"name": local_argv['name'],"imageRef": local_argv['imageRef'],"volume_type": local_argv['volume_type'],"metadata": {},"source_replica": local_argv['source_replica'],"consistencygroup_id":local_argv['consistencygroup_id']}}
     token=get_token(provider_name,_service_type,driver_name)
     if token['error']:
         return  {'flag':False, 'msg':'error::{0}'.format(token['error'][0])}
     else:
         headers={"Content-type":"application/json","Accept": "application/json","X-Auth-Token":token['auth_token']}
         url="%s%s"%(token['publicURL'],_url_keyword)
         try:
            data = json.dumps(params)
         except Exception,e:
            data = None

         req = urllib2.Request(url,data,headers)
         respones = urllib2.urlopen(req)
         result=json.loads(respones.read())
         volume_url=result['volume']['links'][0]["href"]
         volume_status_result=get_volume_status(token,volume_url,headers)
         if volume_status_result['status'] == 'error':
                 result={'flag':False, 'status':'error'}
                 #return result
         else:result={'flag':True, 'status':'available'}
         #result["volume"]['status']=volume_status_result['status']
         print_log(result)
         run_volume_async(result,callback,volume_id,jid)
         return volume_id
         # return local_argv



#挂载卸载云盘         
def op_volume(provider_name,
              volume_id,
              instance_id,
              op='attach',
              device=None,
              driver_name='nova'):
    local_argv=locals()
    _service_type='nova'
    if op == 'attach':
           _url_keyword='/servers/%s/os-volume_attachments'% instance_id
           params={"volumeAttachment":{"volumeId":volume_id,"device": device} }
    else:_url_keyword='/servers/%s/os-volume_attachments/%s'% (instance_id,volume_id)
    data_result={'data':[],'error':[]}
    token=get_token(provider_name,_service_type,driver_name)
    if token['error']:
         return {'flag':False, 'msg':'error::{0}'.format(token['error'][0])}
    else: 
         headers={'X-Auth-Token':token['auth_token'],'Content-Type':'application/json'}
         url="%s%s"%(token['publicURL'],_url_keyword)
         try:
            data = json.dumps(params)
         except Exception,e:
            data = None
         req = urllib2.Request(url,data,headers)
         try:
               if op == 'attach':
                       respones = urllib2.urlopen(req)
               elif op == 'detach':
                       req.get_method = lambda:'DELETE'
                       respones = urllib2.urlopen(req)
         except urllib2.HTTPError,e:      
                   data_result['error'].append({e.code:e.read()})
                   local_argv['error']=data_result['error'][0]
                   print_log(local_argv)                
                   return json.dumps({'flag':False, 'msg':data_result['error'][0]})
         else:     
                   if op == 'detach':
                          result='detach success!!!'
                   else:
                          result=respones.read()
                          local_argv['result']=result
                          print_log(local_argv)
                   return json.dumps({'flag':True, 'msg':result})


#删除卷
def delete_volumes(volume_id,
                   provider_name,
                   driver_name):
          data_result={"error":[]}
          _url_keyword='/volumes/%s'%volume_id
          token=get_token(provider_name,_service_type,driver_name)
          if token['error']:
                     return  {'flag':False, 'msg':'error::{0}'.format(token['error'][0])}
          else:
                 headers={"Content-type":"application/json","Accept": "application/json","X-Auth-Token":token['auth_token']}
                 url="%s%s"%(token['publicURL'],_url_keyword)
                 try:
                       data = json.dumps(params)
                 except Exception,e:
                       data = None 
                 try:
                      req = urllib2.Request(url,data,headers)
                      req.get_method = lambda:'DELETE'
                      respones = urllib2.urlopen(req)                 
                 except urllib2.HTTPError,e:
                      e_read=json.loads(e.read())
                      data_result['error'].append(e_read)
                      return {'flag':False,"msg":data_result}
                 else:
                      return {'flag':True}            
#salt 异步操作格式
def abcd():
     RET = 'menkeyi_callback'
     TGT = 'master-minion'
     FUN = 'cmd.run'
     #id = kwargs.pop('jid')
     LOCAL = salt.client.LocalClient()
     #kwarg={
     #    "volume_id":"aaaaaaaaaaaaaaaaa",
     #    "id":id
     #}
     kwarg={
         "cmd":"echo 11111",
         "aaa":"menkeyi"
     }
     ret = LOCAL.cmd(TGT, FUN, ret=RET,kwarg=kwarg)
     return ret
