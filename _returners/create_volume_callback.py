import json
import urllib2
import salt.utils



def returner(ret):
       jid=ret['jid']
       post_url=ret['fun_args'][0]['post_url']
       result=ret['fun_args'][0]['result']
       result={'jid':jid,'data':result}
       data=json.dumps(result)
       headers ={"Content-type":"application/json","Accept": "application/json"}
       req = urllib2.Request(post_url,data,headers)
       respones = urllib2.urlopen(req)
       with salt.utils.fopen('/tmp/menkeyi_callback.log', 'a+') as fp_:            
                          fp_.write('jid:\n%s\npost_url:\n%s\nresult:\n%s\n'%(jid,post_url,result))
       return ret
