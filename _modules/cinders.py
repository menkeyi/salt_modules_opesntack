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
 #local_argv是函数的定义的参数def xxx(a,b,c,d).kwargs则是def(a,b,c,d,**kwargs)中的kwargs
def validate(local_argv,kwargs):
       #筛选出多余的参数
       #set(kwargs)-set(local_argv)  利用集合方法找出2个字典中的差集，差集就是多出的参数
       if kwargs:extra_fun=set(kwargs)-set(local_argv)

       for k,v in local_argv.items():
            #None 、True、False 特殊类型这样我就不做过滤直接跳过
            if v == None or v == True or v == False :continue
            local_argv[k]=v.strip()
            #这里对类型做出了验证和矫正，当别人调用的时候传递可能为字符串“true”
            #“==”  这种方式是对值的对比，这里其实也可以改成if v in  [True,true]
            if v.strip() == "True" or v.strip() == "true":local_argv[k]=True
            elif v.strip() == "False" or v.strip() == "false":local_argv[k]=False
            elif v.strip() == "" :local_argv[k]=None
       try:
            #利用python思想吧，把try当if用，如果存在extra_fun那么就加入local_argv的字典中。
            #这里转成列表是因为，set只对比key，对比后的结果也只会保留key
            local_argv["extra_fun"]=list(extra_fun) 
       except Exception,e:
            #预料把暂时不知道做什么
            pass
       return local_argv
   

#打印日志，这里写的比较简单就不解释了
def print_log(argv):
      log_path='/tmp/volume.log'       
      with salt.utils.fopen(log_path, 'a+') as fp_:
                            for i in argv:
                                 fp_.write("%s:\n%s\n"%(i,argv[i]))

#获取Provider信息，这个方法是根据公司的逻辑来处理的。公司对账户密码会写到一个文件里面yaml格式
def get_Provider_info(provider_name,driver_name='nova'):
        import yaml
        data={'data':[],'error':[]}
        #文件的命名规则 死的，拼接一下就可以
        file_name='%s_%s.conf'%(provider_name,driver_name)
        #目录也是死的
        Provider_dir='/etc/salt/cloud.providers.d/'
        #目录加文件名拼接
        provider_file='%s%s'%(Provider_dir,file_name)
        try:
            #读取yaml文件
            pro_info=yaml.load(file(provider_file))
            #获取yaml指定的信息，根据拿到的信息可以访问openstack api
            identity_url,user,password,tenant,=pro_info[provider_name]['identity_url'],pro_info[provider_name]['user'],pro_info[provider_name]['password'],pro_info[provider_name]['tenant']
        except Exception,e:
                   #打开文件失败还是什么问题就直接存储到字典中返回
                   data['error'].append(e)
                   data['error'].append(provider_name)
                   return  data
        else:
                 #这里拼了一个字典，循环固定的字符串'user','password','tenant','identity_url'
                 #利用i:eval(i)  组成字典。例：{'user':'admin'},eval(i)将i字符串转换成上面获取的值，比如i=user
                 #那么user就是这个值pro_info[provider_name]['user']
                 for i in 'user','password','tenant','identity_url':
                          data['data'].append({i:eval(i)})
                 return data

#按照_service_type查找对应的endport
def get_serviceCatalog(obj_service,service_type):
     #定义一下字典结构'publicURL':'','tenan_id'  openstack中有的
      data={'publicURL':'','tenan_id':'','error':[]}
      for i in range(len(obj_service)):
          for k  in obj_service[i].keys():
              try:
                   if k == 'name' and  obj_service[i][k] == str(service_type):
                       #根据service_type来找到对应的url。publicURL
                       data['publicURL']= obj_service[i]["endpoints"][0]["publicURL"]
                       #data['tenan_id']=obj_service[i]["endpoints"][0]["id"]
              except Exception,e:
                  data['error'].append(e)
      return  data


#获取token
def get_token(provider_name,service_type,driver_name='nova'):
   data={'data':[],'error':[]}
   #_url_keyword实际就是http://xxx.xxx.xxx/tokens  这个东西，每个服务都有可能不一样这个需要看看openstack api
   _url_keyword='/tokens'
   #username,password,url,tenan_user=Get_Provider_info(provider_name,driver_name)
   #获取openstack的用户、密码、租户、url
   result=get_Provider_info(provider_name,driver_name)
   if result['error']:
           return result
   else:
       # globals().update({k:v}) 。全局变量命名空间，这个函数的。result['data']中包含openstack用到的信息
       #{'user':'admin'},{'password','admin'},globals().update作用就是将字典转换成变量，现在就可以直接用user这个变量了
       #user=admin
       for i in result['data']:
           for k,v in i.items():
                  globals().update({k:v})
   #拼接openstack api访问地址
   url='%s%s'%(identity_url,_url_keyword)
   #这里需要注意一下，总部用的是keyston v2.0的协议，官方搭建的时候用的是V3  下面参数有区别
   params=json.dumps(
          {"auth":{"passwordCredentials":{"username":user, "password":password}, "tenantName":tenant}})
   #rest api 根据http头中"Content-type":"application/json"  来判断是不是一个rest api 的请求
   headers ={"Content-type":"application/json","Accept": "application/json"}
   #这里没有抓取urllib2的错误信息，如果出错的话返回404 urllib2直接抛异常
   req = urllib2.Request(url,params,headers)
   respones = urllib2.urlopen(req)
   result=json.loads(respones.read())
   #servicecatlog: {'tenan_id': u'82cbcefb2e7d495596aaffe4cf9feb10', 'publicURL': u'http://10.20.100.3:8776/v2/80b9ec45d67946eea03d476463a8883c'
   #上面是返回的值，这里需要去=get_serviceCatalog拿去对应的service_type，说简单就是服务端点，每个服务端点都不是固定的
   #openstack sdk 也是这么做的
   data_dic=get_serviceCatalog(result['access']['serviceCatalog'],service_type)
   data_dic['tenan_id']= result['access']['token']['tenant']['id']
   #获取token，然后增加到data_dic
   data_dic['auth_token']=result['access']['token']['id']
   #{'auth_token': u'gAAAAABX1jjHZs3lC8Hyl5scYU_uGg8MPfmojHwTolUXGnj5iauArG-MH3subD0D9rLLfl8l2lTmKAf4SZkggdxLm6stw95bP-Ny7kvPbkzlS47RQyUUfh521_zgZuyQIu1cRaLwhZmKoNaLBVeA8bVYf2ir-D0oi3NrH_Cxu_rNRHLfBptC7T0', 'tenan_id': u'80b9ec45d67946eea03d476463a8883c', 'publicURL': u'http://10.20.100.3:8776/v2/80b9ec45d67946eea03d476463a8883c'
   #print  data_dic'''
   #上面是数据格式，主要就是
   return data_dic




#获取云盘列表(自动上报)
#因为整体业务就是调用api，所以这里就需要同步数据的问题。虽然写了这个方法但是通过api的方法处理还是感觉不是什么好办法
def  get_volumes_list(provider_name,
                      driver_name='nova'):
     _url_keyword='/volumes/detail'
     token=get_token(provider_name,_service_type,driver_name)
     if token['error']:
         return json.dumps({'flag':False, 'msg':'error::{0}'.format(token['error'][0])})
     else:
         headers={'X-Auth-Token':token['auth_token']}
         url="%s%s"%(token['publicURL'],_url_keyword)
         #urllib2 get方法就是将data内容等于空
         data = None
         req = urllib2.Request(url,data,headers)
         respones = urllib2.urlopen(req)
         result=json.loads(respones.read())
     #对数据进行处理一下，因为java对一些字符串无法处理。用pop的好处就是删除旧的数据并且返回值。
     for i in range(len(result['volumes'])):
         result['volumes'][i]["os_vol_host_attr_host"]=result['volumes'][i].pop("os-vol-host-attr:host")
         result['volumes'][i]["os_vol_mig_status_attr_migstat"]=result['volumes'][i].pop("os-vol-mig-status-attr:migstat")
         result['volumes'][i]["os_vol_tenant_attr_tenant_id"]=result['volumes'][i].pop("os-vol-tenant-attr:tenant_id")
         result['volumes'][i]["os_vol_mig_status_attr_name_id"]=result['volumes'][i].pop("os-vol-mig-status-attr:name_id")
         #对数据格式处理
         for x,v  in result['volumes'][i].items():
             if x == "bootable":
                 if x:result['volumes'][i][x]=True
                 else:result['volumes'][i][x]=False
     return  result


#获取云盘状态，主要盘对云盘的状态
def get_volume_status(token,
                      volume_url,
                      headers):
        data_result={"status":'',"error":[]}
        #默认300秒，5分钟。5分钟之内状态不能变成可用我这也算失败。
        #openstack 如果根据镜像创建卷的话需要先拉下来然后在创建这样时间就会很长了
        i=300
        data=None
        req = urllib2.Request(volume_url,data,headers)
        try:
            while i > 1:
                 #每秒获取获取一下状态
                 respones = urllib2.urlopen(req)
                 result=json.loads(respones.read())    
                 if result['volume']["status"] == 'available' or result['volume']["status"]=="error":
                     status=result['volume']["status"]
                     data_result["status"]=status
                     break
                 #写注释的时候发现这里写的不妥因为不需要每秒都连接吧？10秒一次也行啊 。或者按照创建类型来动态更改
                 time.sleep(1)
                 i-=1
        except Exception,e:
                data_result["error"].append(e)
                return data_result
        return data_result


#run_volume_async
def  run_volume_async(result,post_url,id_,jid):
     #主要是这个RET定义了  saltstack 将去找这个回调方法
     RET = 'create_volume_callback'
     TGT = 'master-minion'
     FUN = 'cmd.run'
     LOCAL = salt.client.LocalClient()
     #说下cmd的用处，实际上这里必须执行一个salt可执行命令然后才能回调(自己理解的)
     kwarg={
         "cmd":'date',
         "result":result,
         "post_url":post_url,
         "id":id_,
         "jid":jid,
     }
     ret = LOCAL.cmd(TGT, FUN,ret=RET,jid=jid,kwarg=kwarg)
     return ret

#创建云盘，这是一个异步操作，saltstack
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
     #参数中volume_id 是跟java人员定义的，根据这个id好修改卷状态即可
     #获取局部命名空间变量，这里是做参数判断和验证工作
     local_argv=locals()
     if kwargs:
         #因为是用salstack的原因，这里会多传递很多参数，需要过滤一下，下面只包含方法传递的参数和多余的参数
         kwargs=local_argv.pop("kwargs")["__pub_arg"][0]
     else:kwargs={}
     #参数处理
     local_argv=validate(local_argv,kwargs)
     #写入日志
     print_log(local_argv)
     try:
          #这里没有怎么写以后有需要看看在干点什么
          local_argv["extra_fun"]
     except Exception:
            pass
     #jid公司以后可能传递这个参数这里我自己拼接了一个
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
         #rest api 有规定当创建操作完成的时候会返回创建的内容，这里可以取到创建后的卷的详细资源位置
         volume_url=result['volume']['links'][0]["href"]
         #根据资源位置判断卷的创建状态
         volume_status_result=get_volume_status(token,volume_url,headers)
         if volume_status_result['status'] == 'error':
                 result={'flag':False, 'status':'error'}
                 #return result
         else:result={'flag':True, 'status':'available'}
         #result["volume"]['status']=volume_status_result['status']
         print_log(result)
         #运行异步命令
         run_volume_async(result,callback,volume_id,jid)
         return volume_id
         # return local_argv



#挂载卸载云盘 ，这里的过程写的有写紧了应该在拆分一下
def op_volume(provider_name,
              volume_id,
              instance_id,
              op='attach',
              device=None,
              driver_name='nova'):
    local_argv=locals()
    _service_type='nova'
    #挂载和卸载的参数是有区别的
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
               #attach挂载，detach卸载
               if op == 'attach':
                       respones = urllib2.urlopen(req)
               elif op == 'detach':
                       #urllib2本什么没有delete方法，但是可以通过这个方式来完成
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


#删除卷，删除本什么没有什么太特殊的地方这里就不备注了
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
