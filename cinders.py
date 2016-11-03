#_*_coding:utf8_*_
#!/usr/bin/env python
import urllib
import urllib2
import json
import os



#测试
def abc():
   aaaa='aa'
   return "aaaaaaaaaaa"


#获取Provider信息
def get_Provider_info(provider_name='test_opss',driver_name='nova'):
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
def get_token(provider_name='test_opss',driver_name='nova',service_type='glance'):
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


#获取镜像列表
def Get_glances_list():
     _service_type='glance'
     _url_keyword='/v2.0/images'
     #token=get_token('http://10.20.100.3:5000/v2.0/tokens','admin','admin','admin',_service_type)
     token=get_token(_service_type)
     if token['error']>0:
         return json.dumps({'flag':False, 'msg':token['error']})
     else:
         headers={'X-Auth-Token':token['auth_token']}
         url="%s%s"%(token['publicURL'],_url_keyword)
         data = None
         req = urllib2.Request(url,data,headers)
         respones = urllib2.urlopen(req)
         result=json.loads(respones.read())
         for img in result['images']:
             print img['name']
     return  result


#获取云盘列表
def  get_volumes_list(provider_name='test_opss',driver_name='nova'):
     _service_type='cinderv2'
     _url_keyword='/volumes'
     token=get_token(provider_name,driver_name,_service_type)
     if token['error']:
         return json.dumps({'flag':False, 'msg':'error::{0}'.format(token['error'][0])})
     else:
         headers={'X-Auth-Token':token['auth_token']}
         url="%s%s"%(token['publicURL'],_url_keyword)
         data = None
         req = urllib2.Request(url,data,headers)
         respones = urllib2.urlopen(req)
         result=json.loads(respones.read())
     print  result
     return json.dumps({'flag':True, 'msg':result})

#创建云盘列表
def create_volumes(size=1,
                   provider_name='test_opss',
                   driver_name='nova',
                   name='test000001',
                   description=None,
                   source_volid=None,
                   volume_type=None,
                   availability_zone='nova',
                   imageRef=None,
                   source_replica=None,
                   consistencygroup_id=None,
                   multiattach=False,
                   snapshot_id=None):
     


     _service_type='cinderv2'
     _url_keyword='/volumes'
     params={"volume":{"size":size,"availability_zone": availability_zone,"source_volid":source_volid,"description":description,"multiattach ":multiattach,"snapshot_id": snapshot_id,"name": name,"imageRef": imageRef,"volume_type": volume_type,"metadata": {},"source_replica": source_replica,"consistencygroup_id":consistencygroup_id }}
     token=get_token(provider_name,driver_name,_service_type)
     if token['error']:
         return  json.dumps({'flag':False, 'msg':'error::{0}'.format(token['error'][0])})
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
     print  result
     return json.dumps({'flag':True, 'msg':result})


def op_volume(provider_name='idc_test',
                  driver_name='nova',
                  volume_id='ed80b7d2-f40c-4cdc-bfa7-eb3d266ce7a4',
                  instance_id='2603fc92-d6e7-4890-b64c-e3879981d81b',
                  op='attach',
                  device=None):
    _service_type='nova'
    if op == 'attach':
           _url_keyword='/servers/%s/os-volume_attachments'% instance_id
           params={"volumeAttachment":{"volumeId":volume_id,"device": device} }
    else:_url_keyword='/servers/%s/os-volume_attachments/%s'% (instance_id,volume_id)
    data_result={'data':[],'error':[]}
    token=get_token(provider_name,driver_name,_service_type)
    if token['error']:
         return json.dumps({'flag':False, 'msg':'error::{0}'.format(token['error'][0])})
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
                   return json.dumps({'flag':False, 'msg':data_result['error'][0]})
         else:     
                   if op == 'detach':
                          result="detach success!!!"
                   else:result=json.loads(respones.read())
                   return json.dumps({'flag':True, 'msg':result})
