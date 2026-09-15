"""Handshake TLS real com CA efêmera e socketpair, sem Internet."""
import socket
import ssl
import subprocess
import threading
import pytest
from argos.infrastructure.scrapers.pinned_tls import PinnedTLSConnection

@pytest.fixture
def certificate(tmp_path):
    cert=tmp_path/'cert.pem';key=tmp_path/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=www.mercadolivre.com.br','-addext','subjectAltName=DNS:www.mercadolivre.com.br'],check=True,capture_output=True)
    return cert,key

@pytest.mark.parametrize('hostname,success',[('www.mercadolivre.com.br',True),('produto.mercadolivre.com.br',False)])
def test_real_tls_verifies_original_hostname(monkeypatch,certificate,hostname,success):
    cert,key=certificate
    client,server=socket.socketpair()
    original_socket=socket.socket
    class ConnectedSocket(original_socket):
        def connect(self,destination):
            assert destination==('8.8.8.8',443)
    connected=ConnectedSocket(fileno=client.detach())
    server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert,key)
    client_context=ssl.create_default_context(cafile=str(cert))
    names=[]
    server_context.set_servername_callback(lambda sock,name,ctx:names.append(name))
    errors=[]
    def serve():
        try:
            with server_context.wrap_socket(server,server_side=True) as tls:
                tls.recv(1)
        except ssl.SSLError:
            errors.append('handshake_rejected')
        finally:
            server.close()
    thread=threading.Thread(target=serve);thread.start()
    monkeypatch.setattr('socket.socket',lambda *a,**k:connected)
    monkeypatch.setattr('ssl.create_default_context',lambda:client_context)
    pinned=PinnedTLSConnection(f'https://{hostname}/p/MLB123','8.8.8.8')
    try:
        if success:
            tls=pinned.connect()
            tls.sendall(b'x')
            assert tls.version() is not None
        else:
            with pytest.raises(RuntimeError,match='transport_failed'):
                pinned.connect()
    finally:
        pinned.close();connected.close();thread.join(timeout=5)
    assert not thread.is_alive()
    assert names==[hostname]
