import asyncio
import os
import subprocess
from aiohttp.web import Application, Response, MsgType, WebSocketResponse

WS_FILE = os.path.join(os.path.dirname(__file__), 'websocket.html')


@asyncio.coroutine
def wshandler(request):
    resp = WebSocketResponse()
    ok, protocol = resp.can_start(request)
    if not ok:
        with open(WS_FILE, 'rb') as fp:
            return Response(body=fp.read(), content_type='text/html')
    yield from resp.prepare(request)
    request.app['sockets'].append(resp)

    while True:
        msg = yield from resp.receive()
        print('msg: {}'.format(msg.data))
        if msg.tp == MsgType.text:
            for ws in request.app['sockets']:
                ws.send_str('---------------')
                if msg.data == 'on':
                    ws.send_str(turnOn())
                elif msg.data == 'off':
                    ws.send_str(turnOff())
                elif msg.data == 'true':
                    f = open("cb_state.txt",'w')
                    f.write('1')
                    f.close()
                elif msg.data == 'false':
                    f = open("cb_state.txt",'w')
                    f.write('0')
                    f.close()
                else:
                    f = open("cb_state.txt")
                    ws.send_str(f.read())
                    f.close()
        else:
            break
    request.app['sockets'].remove(resp)
    return resp


@asyncio.coroutine
def init(loop):
    app = Application(loop=loop)
    app['sockets'] = []
    app.router.add_route('GET', '/', wshandler)
    handler = app.make_handler()
    srv = yield from loop.create_server(handler, '127.0.0.1', 8080)
    return app, srv, handler

def turnOn():
    cmd = 'net start browser'
    PIPE = subprocess.PIPE
    p = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
        stderr=subprocess.STDOUT)
    while True:
        s = p.stdout.readline()
        if not s: break
        elif s.decode('cp866').count('успешно запущена.') > 0: return 'Сервис работает'
        elif s.decode('cp866').count('ошибка 5') > 0: return 'Отказано в доступе'
    return 'Сервис остановлен'

def turnOff():
    cmd = 'net stop browser'
    PIPE = subprocess.PIPE
    p = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
        stderr=subprocess.STDOUT)
    while True:
        s = p.stdout.readline()
        if not s: break
        elif s.decode('cp866').count('успешно остановлена.') > 0: return 'Сервис остановлен'
        elif s.decode('cp866').count('ошибка 5') > 0: return 'Отказано в доступе'
    return 'Сервис работает'

try:
    f = open("cb_state.txt")
    f.close()
except IOError:
    f = open("cb_state.txt",'w')
    f.write('1')
    f.close()
loop = asyncio.get_event_loop()
app, srv, handler = loop.run_until_complete(init(loop))
print('Server started at {}. Hit CTRL+C to stop'.format(srv.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
print('Server shutting down.')
loop.close()
