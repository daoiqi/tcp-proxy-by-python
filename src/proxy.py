#!/usr/bin/env python
# coding: utf-8

import time
import socket
import socks  #third part plugin
import threading,signal,os,sys
import ConfigParser,copy,re


def log(msg):
    print '[%s] %s' % (time.ctime(),msg)


is_exit = False


class ForwardServer(object):
    PAGE_SIZE = 4096

    def __init__(self):
        self.listen_host = None
        self.listen_port = None
        self.remote_host = None
        self.remote_port = None
        self.proxy_host = None
        self.proxy_port = None

    def setListen(self,host,port):
        self.listen_host = host
        self.listen_port = port
        return self

    def setRemote(self,host,port):
        self.remote_host = host
        self.remote_port = port
        return self

    def setProxySocks5(self,host,port):
        self.proxy_host = host
        self.proxy_port = port
        return self

    def _listen(self):
        sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #tcp
        sock_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_server.bind((self.listen_host, self.listen_port))
        sock_server.listen(5)
        log('Listening at %s:%d ...' % (self.listen_host, self.listen_port))
        return sock_server

    def serve(self):
        sock_server = self._listen()

        while not is_exit:
            try:
                sock, addr = sock_server.accept()
            except (KeyboardInterrupt, SystemExit):
                log('Closing...')
                sock_server.shutdown(socket.SHUT_RDWR)
                sock_server.close()
                #sys.exit(0)
                break
            except Exception:
                log('exception exit')
                sock_server.shutdown(socket.SHUT_RDWR)
                sock_server.close()
                #sys.exit(-1)
                break

            threading.Thread(target=self._forward, args=(sock,) ).start()
            log('New clients from %s:%d' % addr)

        log('exit server')

    def _forward(self,sock_in):
        sock_out = None
        try:
            print self.remote_host,self.remote_port
            sock_out = ForwardClient(self.remote_host,self.remote_port,self.proxy_host,self.proxy_port).getClient()
            log('get the client socks done')
        except Exception, e:
            log('get Remote Client error: %s' % str(e))
            raise e
            return

        threading.Thread(target=self._do_data_forward, args=(sock_in, sock_out)).start()
        threading.Thread(target=self._do_data_forward, args=(sock_out, sock_in)).start()

    def _do_data_forward(self,sock_in,sock_out):
        addr_in = '%s:%d' % sock_in.getpeername()
        addr_out = '%s:%d' % sock_out.getpeername()

        while True:
            try:
                data = sock_in.recv( ForwardServer.PAGE_SIZE )
            except Exception, e:
                log('Socket read error of %s: %s' % (addr_in, str(e)))
                break

            if not data:
                log('Socket closed by ' + addr_in)
                break

            try:
                sock_out.sendall(data)
            except Exception, e:
                log('Socket write error of %s: %s' % (addr_out, str(e)))
                break

            log('%s -> %s (%d B)' % (addr_in, addr_out, len(data)))

        sock_in.close()
        sock_out.close()


class ForwardClient(object):
    def __init__(self,host,port,proxy_host=None,proxy_port=None):
        self.remote_host = host
        self.remote_port = port
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def setRemote(self,host,port):
        self.remote_host = host
        self.remote_port = port
        return self

    def setProxySocks5(self,host,port):
        self.proxy_host = host
        self.proxy_port = port
        return self

    def getClient(self):
        sock_out = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
        if self.proxy_host is not None and self.proxy_port is not None:
            sock_out.setproxy(socks.PROXY_TYPE_SOCKS5, self.proxy_host, self.proxy_port)
            log('using socks proxy %s:%d' % ( self.proxy_host,self.proxy_port))

        try:
            print 'remote,=',(self.remote_host, self.remote_port)
            sock_out.connect((self.remote_host, self.remote_port))
        except socket.error, e:
            sock_out.close()
            log('Remote connect error: %s' % str(e))
            raise Exception,'Remote connect error: %s' % str(e)

        return sock_out




def handler(signum, frame):
    print signum , frame
    global is_exit
    is_exit = True
    print "receive a signal %d, is_exit = %d"%(signum, is_exit)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    #options = Config().parser('proxy.ini')
    #print options
    listen = ("127.0.0.1", 3307)
    remote = ("127.0.0.1", 3306)
    args = listen + remote
    serv = ForwardServer()
    serv.setListen(listen[0], listen[1])
    serv.setRemote(remote[0], remote[1])
    serv.serve()
    # start()



