import random
import sys
from collections import OrderedDict
from flask import render_template, url_for, request
from app import getResult, webapp, memcache, memcacheStatistics,memcacheConfig
from flask import json
import datetime
import mysql.connector



@webapp.route('/clear')
def clearCache():
    t=datetime.datetime.now()
    memcacheStatistics.addRequestTime(t)
    
    memcache.clear()
    memcacheStatistics.clear()
    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )
    return response
    
@webapp.route('/invalidateKey/<key>')   
def invalidateKey(key):
    t=datetime.datetime.now()
    memcacheStatistics.addRequestTime(t)
    if key in memcache:
        value = memcache[key]
        size=sys.getsizeof(value)
        memcacheStatistics.removeItem(size)
        del memcache[key]
        response = webapp.response_class(
            response=json.dumps("OK"),
            status=200,
            mimetype='application/json'
        )
        
    else:
        response = webapp.response_class(
            response=json.dumps("Unknown key"),
            status=400,
            mimetype='application/json'
        )
        
    return response
    
    
    
@webapp.route('/refreshConfiguration')   
def refreshConfiguration():
    t=datetime.datetime.now()
    memcacheStatistics.addRequestTime(t)
    cnx = mysql.connector.connect(user='scott', password='password',
                              host='127.0.0.1',
                              database='employees')
    cursor = cnx.cursor()
    query =  "SELECT `capacity`, `lru` FROM memcache_config;"
    cursor.execute(query)
    memcacheConfig.capacity = cursor[0]
    if cursor[1]:
        memcacheConfig.policy = 'LRU'
    else:
        memcacheConfig.policy = 'Random'
    
    cursor.close()
    cnx.close()
    while (memcacheStatistics.get_size() > memcacheConfig.capacity*1024*1024):
        if memcacheConfig['policy'] == 'LRU':
            delvalue=memcache.popitem(False)[1]
            size=sys.getsizeof(delvalue)
            memcacheStatistics.removeItem(size)
        else:
            delkey=random.choice(list(memcache.keys()))
            delvalue = memcache[delkey]
            size=sys.getsizeof(delvalue)
            memcacheStatistics.removeItem(size)
            del memcache[delkey]
    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
        )
    return response
    
    
@webapp.route('/get',methods=['POST'])
def get():
    t=datetime.datetime.now()
    memcacheStatistics.addRequestTime(t)
    
    key = request.form.get('key')
    if key in memcache:
        value = memcache[key]
        r=getResult(t, 'hit')
        memcacheStatistics.addGetResult(r)
        
        if memcacheConfig['policy'] == 'LRU':
            memcache.move_to_end(key) 
            
        response = webapp.response_class(
            response=json.dumps(value),
            status=200,
            mimetype='application/json'
        )
    else:
        r=getResult(t, 'miss')
        memcacheStatistics.addGetResult(r)
        response = webapp.response_class(
            response=json.dumps("Unknown key"),
            status=400,
            mimetype='application/json'
        )

    return response

@webapp.route('/put',methods=['POST']) 
def put():
    """
    image_string = ""
    with open(address, "rb") as image:
        image_string = base64.b64encode(image.read())
    data = dict(key=key, value=image_string)
    response = requests.post("http://localhost:5001/put", data=data)
    """
    t=datetime.datetime.now()
    memcacheStatistics.addRequestTime(t)
    
    key = request.form.get('key')
    value = request.form.get('value')
    image_size = sys.getsizeof(value)
    if key in memcache:
        delvalue = memcache[key]
        size=sys.getsizeof(delvalue)
        memcacheStatistics.removeItem(size)
        del memcache[key]
    if image_size > memcacheConfig.capacity*1024*1024:
        response = webapp.response_class(
        response=json.dumps("Image too big to cache"),
        status=200,
        mimetype='application/json'
        )
        return response
    
    while (image_size + memcacheStatistics.get_size() > memcacheConfig.capacity*1024*1024):
        if memcacheConfig['policy'] == 'LRU':
            delvalue=memcache.popitem(False)[1]
            size=sys.getsizeof(delvalue)
            memcacheStatistics.removeItem(size)
        else:
            delkey=random.choice(list(memcache.keys()))
            delvalue = memcache[key]
            size=sys.getsizeof(delvalue)
            memcacheStatistics.removeItem(size)
            del memcache[delkey]
            
    memcache[key] = value
    memcacheStatistics.addItem(image_size)
    if memcacheConfig['policy'] == 'LRU':
        memcache.move_to_end(key) 
        
    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )

    return response


@webapp.route('/statistic') 
def statistic():
    s=memcacheStatistics.getStat()
    
    cnx = mysql.connector.connect(user='scott', password='password',
                              host='127.0.0.1',
                              database='employees')
    cursor = cnx.cursor()
    query =  ("INSERT INTO statistics "
                "(`itemNum`, `totalSize`, `requestNum``missRate`, `hitRate`)" 
                "VALUES ( {}, {}, {}, {}, {});")
    cursor.execute(query,s)
    
    cnx.commit()
    cursor.close()
    cnx.close()
    
    response = webapp.response_class(
        response=json.dumps('OK'),
        status=200,
        mimetype='application/json'
    )

    return response