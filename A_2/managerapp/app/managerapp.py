"""
 * managerapp.py
 * manager app page
 *
 * Author: Haotian Chen
 * Date: Nov. 8, 2022
"""


import base64
import os
from io import BytesIO

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mysql.connector
import requests
from flask import escape, g, jsonify, render_template, request
from werkzeug.utils import secure_filename

from . import manager, managerfunc

#variables
policy = 'lru'
capacity= 4
minrate='15' 
maxrate='75' 
expand='1' 
shrink='1'
def draw_charts(stats:list, y_label:str, title:str):
    """Draw the charts for the statistics.

    Args:
      stats (list): the list of statistics.

    Returns:
      encoded_img (str): the encoded image of the chart.
    """
    # draw the charts
    x1 = [x for x in range(len(stats))]
    l1 = plt.plot(x1, stats, 'r')
    plt.xlabel('Time')
    plt.ylabel(y_label)
    plt.title(title)
    sio = BytesIO()
    plt.savefig(sio, format='png')
    #base64encode
    data = base64.encodebytes(sio.getvalue()).decode()
    src = 'data:image/png;base64,{}'.format(data)
    plt.close()
    return src
    

@manager.route('/')
def get_home():
    """Home page render.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    y_label = ['numberItems', 'currentSize', 'totalRequests', 'missRate', 'hitRate']
    title = ['numberItems', 'currentSize', 'totalRequests', 'missRate', 'hitRate']
    result = []
    stat1 = [x for x in range(30)]
    stat2 = [2*x for x in range(50)]
    stat3 = [3*x for x in range(30)]
    stat4 = [4*x for x in range(30)]
    stat5 = [5*x for x in range(30)]
    stats = [stat1, stat2, stat3, stat4, stat5]
    num = 0
    # stats = managerfunc.getAggregateStat30Mins()
    # num = managerfunc.num_running()
    for i in [0,1,2,3,4]:    
        result.append((draw_charts(stats[i], y_label[i], title[i])))
        
    return render_template('index.html',numofinstance=num, src1=result[0], src2=result[1], src3=result[2], src4=result[3], src5=result[4])





#render config page
@manager.route('/config')
def get_config():
    """Configuration page render.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    #pool = managerfunc.num_running()
    pool = 5

    return render_template('config.html', poli=policy, capa=capacity, pool=pool, minrate=minrate, maxrate=maxrate, expand=expand, shrink=shrink)

#return memcahce policy and capacity for frontend
@manager.route('/memcacheconfig')
def get_memcacheconfig():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    memconfig = {
      'policy': policy,
      'capacity': capacity
    }

    return jsonify(memconfig)
  
  
#return scaler settings for auto scaler
@manager.route('/scalerconfig')
def get_scalerconfig():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    scalerconfig = {
      'minrate': minrate,
      'maxrate': maxrate,
      'expand': expand,
      'shrink': shrink
    }

    return jsonify(scalerconfig)

#update memcache policy and capacity
@manager.route('/putMemcacheConfig', methods=['POST'])
def put_memcacheconfig():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    global policy
    global capacity
    policy = request.form['policy']
    capacity = request.form['capacity']
    return render_template('result.html', result='Your Request Has Been Processed :)')

#update scaler settings
@manager.route('/putScalerConfig', methods=['POST'])
def put_scalerconfig():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    global minrate
    global maxrate
    global expand
    global shrink
    minrate = request.form['minrate']
    maxrate = request.form['maxrate']
    expand = request.form['expand']
    shrink = request.form['shrink']
    return render_template('result.html', result='Your Request Has Been Processed :)')

#return 1min miss rate for auto scaler to use
@manager.route('/1minmiss')
def get_1minmiss():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    missrate = managerfunc.getAggregateMissRate1mins()
    return missrate
  
#return number of instance running for auto scaler to use
@manager.route('/numrunning')
def get_num_running():
    """Configuration page render.

    Args:
      n/a

    Returns:
      json: the arguments for the Jinja template
    """
    num = managerfunc.num_running()
    return num

#return ip of nth instance for auto scaler to use
@manager.route('/ip/<n>')
def get_nth_ip(n):
    """Configuration page render.

    Args:
      n/a

    Returns:
      ip
    """
    ip = managerfunc.get_nth_ip(n)
    return ip

@manager.route('/about')
def get_about():
    """About page render.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    manager.logger.debug('\n* Viewing about')
    return render_template('about.html')



############################################################################################
@manager.route('/setManual', methods=['POST'])
def set_manual():
    """Set the manual mode.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    manager.logger.debug('\n* Setting manual mode')
    response = requests.get("http://localhost:5001/setManual")
    manager.logger.debug(response.text)
    return render_template('result.html', result='Your Request Has Been Processed :)')

@manager.route('/setAuto', methods=['POST'])
def set_auto():
    """Set the auto mode.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    manager.logger.debug('\n* Setting auto mode')
    response = requests.get("http://localhost:5001/setAuto")
    manager.logger.debug(response.text)
    return render_template('result.html', result='Your Request Has Been Processed :)')
  
@manager.route('/deleteData', methods=['POST'])
def delete_data():
    """Delete the data.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    manager.logger.debug('\n* Deleting data')
    response = requests.get("http://localhost:5001/deleteData")
    manager.logger.debug(response.text)
    return render_template('result.html', result='Your Request Has Been Processed :)')
  
@manager.route('/clearMemcache', methods=['POST'])
def clear_memcache():
    """Clear the memcache.

    Args:
      n/a

    Returns:
      str: the arguments for the Jinja template
    """
    manager.logger.debug('\n* Clearing memcache')
    response = requests.get("http://localhost:5001/clear")
    manager.logger.debug(response.text)
    return render_template('result.html', result='Your Request Has Been Processed :)')
############################################################################################


@manager.route('/api/config', methods=['POST'])
def put_config_api():
    """The api to commit the changes in configurations.

    Args:
      n/a

    Returns:
      dict: the JSON format response of the HTTP request
    """

    policy = request.form['policy']
    capacity = request.form['capacity']
    manager.logger.debug('\n* Configuring with capacity: ' + str(capacity) + ' and policy: ' + str(policy))
    cursor = db_wrapper('put_config', policy, capacity)
    if not cursor:
        return {
            'success': 'false',
            'error': {
                'code': 500,
                'message': 'Internal Server Error: Fail in connecting to database'
            }
        }
    if request.form['clear'] == "yes":  # clear the cache
        response = requests.get("http://localhost:5001/clear")
        manager.logger.debug(response.text)
    response = requests.get("http://localhost:5001/refreshConfiguration")
    manager.logger.debug(response.text)
    return {
        'success': 'true'
    }
