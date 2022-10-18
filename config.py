import os

if not os.path.exists('log'):
    os.mkdir('log')


workers = 2
threads = 1
bind = '0.0.0.0:8899'
timeout = 50
backlog = 512
daemon = False
# reload = True
worker_class = 'gevent'
worker_connections = 2000
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s "%(f)s" "%(a)s"'
accesslog = 'log/access.log'
errorlog = 'log/error.log'