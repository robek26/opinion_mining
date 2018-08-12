from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi
import sys
import mimetools
from pprint import pprint
import urlparse
import codecs
import random
import os
import json
from SocketServer import ThreadingMixIn
import threading
from opinionminer.miner import *
import SocketServer

class opinionMiningHandler:
    def write_to_tmp_file(self,data):
        a =  ['a','b','v','r','d','g','h','i','j','k','a','l','1','0','3','4','5','6','8','9','2']
        fname = ''
        for i in range(50):
            fname += a[int(random.random() * len(a))]
        fname += '.csv'
        f = open(fname,'w')
        f.write(data)
        f.close()
        return fname
    
    def fb_sentiment(self,**kwargs):
        # extract parameters
        access_token = kwargs['access_token']
        post_id = kwargs['post_id']
        user_id = kwargs['user_id']
        features = kwargs['features'].split(',')
        features = [i for i in features if i != '']
        limit = kwargs['maxlimit']
        # main operation
        
        result = fetch_fb_sentiment(access_token,user_id,post_id,features,limit = int(limit))
        
        return result
    def op_file_sentiment(self,**kwargs):
        # extract parameters
        data = kwargs['filedata']
        features = kwargs['features'].split(',')
        features = [i for i in features if i != '']
        # main operation
        
        fname = self.write_to_tmp_file(data)
        result = None
        with codecs.open(fname,'r',encoding='utf-8') as lines:
            result = fetch_file_sentiment(lines,features) 
        os.remove(fname)
        
        return result
    def twitter_sentiment(self,**kwargs):
        # extract parameters
        keywords = kwargs['keywords'].split(',')
        features = kwargs['features'].split(',')
        keywords = [i for i in keywords if i != '']
        features = [i for i in features if i != '']
        limit = kwargs['maxlimit']
        print(limit)
        # main operation
        result = fetch_twitter_sentiment(keywords,features,limit = limit)
        
        return result
    
    
PORT_NUMBER = 21000

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
    
    """
    Custom functions to process incoming and outgoing signals
    
    """
    def fetch_params_and_redirect(self,form):
        
        action = form['action'].value
        
        if action == 'fb_sentiment':
            params = {'user_id' : '','post_id' : '','access_token' : '','features' : '','maxlimit' : 0}
            for ky in params:
                params[ky] = form[ky].value
            return self.redirect(action, **params)
        elif action == 'op_file_sentiment':
            params = {'filedata' : None,'features' : ''}
            for ky in params:
                params[ky] = form[ky].value
            return self.redirect(action, **params)
        elif action == 'twitter_sentiment':
            params = {'keywords' : '','features' : '','maxlimit' : 0}
            for ky in params:
                params[ky] = form[ky].value
            return self.redirect(action, **params)
        else:
            params = {}
            return self.redirect(action, **params)
            
        
    def redirect(self,action, **kwargs):
        oph = opinionMiningHandler()
        if action == 'fb_sentiment':
            return oph.fb_sentiment(**kwargs)
        elif action == 'op_file_sentiment':
            return oph.op_file_sentiment(**kwargs)
        elif action == 'twitter_sentiment':
            return oph.twitter_sentiment(**kwargs)
        else:
            return 'UNKNOWN OPERATION'
            
    
   
    
    """
    End of Custom
    
    """
    
    #Handler for the GET requests
    def do_GET(self):
        print('do GET')
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type','text/html') 
        self.end_headers()
        # Send the html message
        self.wfile.write("Hello Client !")
        return

    #Handler for the POST requests
    def do_POST(self):
        pprint (vars(self))
        length = int(self.headers['Content-Length'])
        print(self.headers)
        #post_data = self.rfile.read(length)#.decode('utf-8')
        #print(post_data)
        
        
        
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST'}
        )
       # print(form['userid'].value)
       # print(form['fileToUpload'].value)
        
        
        output = self.fetch_params_and_redirect(form)
        output = json.dumps(output)
        print(output)
        
        # Send back response after the data is processed
        
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type','text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write(output)
        
        
        return
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    
    
    
if __name__ == "__main__":
    PORT_NUMBER = 21000
   
    try:
        #Create a web server and define the handler to manage the incoming request
        server = ThreadedHTTPServer(('', PORT_NUMBER), myHandler)
        print 'Started httpserver on port ' , PORT_NUMBER
        print 'Press Control + C to Exit...'
        #Wait forever for incoming htto requests
        server.serve_forever()

    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        server.socket.close()
    
   
    

     
        
    
    
