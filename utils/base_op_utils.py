# -*- coding: utf-8 -*-
import urllib2
import json
import os
import salt.client
import logging
import time
import salt.utils
from hashlib import sha1






#参数处理
def validate(local_argv,kwargs):
       if kwargs:extra_fun=set(kwargs)-set(local_argv)
       for k,v in local_argv.items():
            try:
                 if v == None or v == True or v == False :continue
                 local_argv[k]=v.strip()         
                 if v.strip() == "True" or v.strip() == "true":local_argv[k]=True
                 elif v.strip() == "False" or v.strip() == "false":local_argv[k]=False
                 elif v.strip() == "" :local_argv[k]=None
            except AttributeError,e:
                   continue
       try:
            local_argv["extra_fun"]=list(extra_fun) 
       except Exception,e:
            pass
       return local_argv
   

#打印日志
def print_log(argv,path='/tmp/volume.log'):
      with salt.utils.fopen(path, 'a+') as fp_:
                            #sp="="*50
                            #for i in argv:
                            #     fp_.write("%s:\n%s\n"%(i,argv[i]))
                            #fp_.write("%s\n"% sp)
                            fp_.write("%s\n"%repr(argv))








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








def base_get_service_list(params):
     error=[]
     if  params.has_key('token'):
         print_log(params,'/tmp/neutron.log')
         kwargs={}
         local_argv=validate(params['token'],kwargs)
         token=params.pop('token')
         token['error']=[]
         mode=token['mode']
         
     else:
         token={}
         api_params=params.pop('api_params')
         service_type=params.pop('service_type') 
         url_keyword=params.pop('url_keyword')
         provider_name=params.pop('provider_name')
         mode=params.pop('mode')
         driver_name=params.pop('driver_name')
         local_argv=params
         #print_log(local_argv,'/tmp/neutron.log')
         if local_argv['kwargs']:
               kwargs=local_argv.pop("kwargs")["__pub_arg"][0]
         else:kwargs={}
         local_argv=validate(local_argv,kwargs)
     try:
          local_argv["extra_fun"]
     except Exception:
            pass
     if not token:token=get_token(provider_name,service_type,driver_name)
     else:url_keyword=token['url_keyword']
     if token['error']:
         return  {'flag':False, 'msg':'error::{0}'.format(token['error'][0])}
     else:
         headers={"Content-type":"application/json","Accept": "application/json","X-Auth-Token":token['auth_token']}
         url="%s%s"%(token['publicURL'],url_keyword)
         if mode == 'get':
              data=None
              req = urllib2.Request(url,data,headers)   
         elif mode == 'post':
              data=json.dumps(eval(api_params))
              req = urllib2.Request(url,data,headers)
         elif mode == 'delete':
              data=None
              req = urllib2.Request(url,data,headers)
              req.get_method = lambda:'DELETE'
              
         try:
              respones = urllib2.urlopen(req)
         except urllib2.HTTPError,e:
                   error.append({e.code:e.read()})
                   #local_argv['error']=data_result['error'][0]
                   return {'flag':False, 'error':error[0]}
         try:
             #print_log(token,'/tmp/neutron.log')
             result=json.loads(respones.read())
         except Exception,e:
             result=True    
                
         return result,token['auth_token']
