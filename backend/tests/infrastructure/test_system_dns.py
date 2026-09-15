import subprocess
import pytest
from argos.infrastructure.scrapers.system_dns import SystemDestinationResolver


def test_subprocess_without_shell_returns_complete_set(monkeypatch):
    def run(command,**kwargs):
        assert command[-1]=='www.mercadolivre.com.br'
        assert kwargs['timeout']==2 and kwargs['check']
        assert 'shell' not in kwargs
        return subprocess.CompletedProcess(command,0,'["8.8.8.8", "::1"]','')
    monkeypatch.setattr('subprocess.run',run)
    assert SystemDestinationResolver().resolve('www.mercadolivre.com.br',timeout=2)==['8.8.8.8','::1']


@pytest.mark.parametrize('failure',[subprocess.TimeoutExpired('dns',1),subprocess.CalledProcessError(1,'dns',stderr='sensitive')])
def test_failure_is_sanitized(monkeypatch,failure):
    def run(*args,**kwargs): raise failure
    monkeypatch.setattr('subprocess.run',run)
    with pytest.raises((TimeoutError,RuntimeError)) as error:
        SystemDestinationResolver().resolve('www.mercadolivre.com.br',timeout=1)
    assert 'sensitive' not in str(error.value)


@pytest.mark.parametrize('timeout',[0,4,float('nan'),float('inf'),True])
def test_invalid_timeout_never_starts_process(monkeypatch,timeout):
    monkeypatch.setattr('subprocess.run',lambda *a,**k:pytest.fail('No subprocess allowed'))
    with pytest.raises(ValueError):
        SystemDestinationResolver().resolve('www.mercadolivre.com.br',timeout=timeout)


def test_unallowed_host_never_starts_process(monkeypatch):
    monkeypatch.setattr('subprocess.run',lambda *a,**k:pytest.fail('No subprocess allowed'))
    with pytest.raises(ValueError):
        SystemDestinationResolver().resolve('localhost',timeout=1)


def test_real_blocking_child_is_terminated(monkeypatch):
    import argos.infrastructure.scrapers.system_dns as module
    monkeypatch.setattr(module,'_SCRIPT','import time; time.sleep(30)')
    import time
    started=time.monotonic()
    with pytest.raises(TimeoutError):
        SystemDestinationResolver().resolve('www.mercadolivre.com.br',timeout=0.2)
    assert time.monotonic()-started<5
