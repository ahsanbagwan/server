import asyncio
import logging
import os
import subprocess
import sys

from PySide.QtCore import QCoreApplication
import pytest
import mock
from PySide import QtCore


if not hasattr(QtCore, 'Signal'):
    QtCore.Signal = QtCore.pyqtSignal

from PySide.QtNetwork import QTcpSocket
from src.players import playersOnline, Player
from games import Game

from src.JsonTransport import Transport

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-20s %(message)s',
                                       '%M:%S'))
logging.getLogger('quamash').setLevel(logging.INFO)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)

import quamash

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete()
    return wrapper


def pytest_pycollect_makeitem(collector, name, obj):
    if name.startswith('test_') and asyncio.iscoroutinefunction(obj):
        return list(collector._genfunctions(name, obj))

def pytest_pyfunc_call(pyfuncitem):
    testfn = pyfuncitem.obj

    if not asyncio.iscoroutinefunction(testfn):
        return

    funcargs = pyfuncitem.funcargs
    testargs = {}
    for arg in pyfuncitem._fixtureinfo.argnames:
        testargs[arg] = funcargs[arg]
    coro = testfn(**testargs)

    loop = testargs.get('loop', asyncio.get_event_loop())
    loop.run_until_complete(coro)
    return True

@pytest.fixture(scope='session')
def application():
    return QCoreApplication([])

@pytest.fixture(scope='function')
def loop(request, application):
    loop = quamash.QEventLoop(application)
    loop.set_debug(True)
    asyncio.set_event_loop(loop)
    additional_exceptions = []

    def finalize():
        sys.excepthook = orig_excepthook
        try:
            loop.close()
        except KeyError:
            pass
        finally:
            asyncio.set_event_loop(None)
            for exc in additional_exceptions:
                if (
                        os.name == 'nt' and
                        isinstance(exc['exception'], WindowsError) and
                        exc['exception'].winerror == 6
                ):
                    # ignore Invalid Handle Errors
                    continue
                raise exc['exception']
    def except_handler(loop, ctx):
        additional_exceptions.append(ctx)
    def excepthook(type, *args):
        loop.stop()
    orig_excepthook = sys.excepthook
    sys.excepthook = excepthook
    loop.set_exception_handler(except_handler)
    request.addfinalizer(finalize)
    return loop

@pytest.fixture
def patch_connectivity(monkeypatch):
    def set_to(level):
        @asyncio.coroutine
        def setter():
            yield from asyncio.sleep(0.001)
            return level
        monkeypatch.setattr('connectivity.TestPeer.determine_connectivity', setter)
    return set_to

@pytest.fixture
def connected_game_socket():
    game_socket = mock.Mock(spec=QTcpSocket)
    game_socket.state = mock.Mock(return_value=QTcpSocket.ConnectedState)
    game_socket.isValid = mock.Mock(return_value=True)
    return game_socket

@pytest.fixture
def transport():
    return mock.Mock(spec=Transport)

@pytest.fixture
def game(players):
    game = mock.MagicMock(spec=Game(1))
    players.hosting.getGame = mock.Mock(return_value=game)
    players.joining.getGame = mock.Mock(return_value=game)
    players.peer.getGame = mock.Mock(return_value=game)
    game.hostPlayer = players.hosting
    game.getInitMode = lambda: 0
    game.packetReceived = []
    game.getGameName = lambda: "Some game name"
    game.getuuid = lambda: 1
    return game

def player(login, id, port, action, ip='127.0.0.1'):
    p = mock.MagicMock(spec=Player)
    p.getGamePort.return_value = port
    p.getAction = mock.Mock(return_value=action)
    p.getLogin = mock.Mock(return_value=login)
    p.getId = mock.Mock(return_value=id)
    p.getIp = mock.Mock(return_value=ip)
    p.action = action
    p.id = id
    p.login = login
    p.address_and_port = "{}:{}".format(ip, port)
    return p

@pytest.fixture
def players():
    return mock.Mock(
        hosting=player('Paula_Bean', 1, 6112, "HOST"),
        peer=player('That_Guy', 2, 6112, "JOIN"),
        joining=player('James_Kirk', 3, 6112, "JOIN")
    )

@pytest.fixture
def player_service(players):
    p = mock.Mock(spec=playersOnline())
    p.findByIp = mock.Mock(return_value=players.hosting)
    return p

@pytest.fixture
def games(game):
    return mock.Mock(
        getGameByUuid=mock.Mock(return_value=game)
    )
