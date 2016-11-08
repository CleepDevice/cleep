import bus
import gpios
import os
import pprint

if __name__ == '__main__':
    bus_ = bus.MessageBus()
    g = gpios.Gpios(bus_)
    g.start()
    pp = pprint.PrettyPrinter(indent=4)

    print('QUIT to quit')
    print('PUSH <command> TO <module>')
    while True:
        input = raw_input('> ')
        if input.lower().startswith('quit'):
            break
        elif input.startswith('PUSH '):
            try:
                (cmd, to) = input[5:].split(' TO ')
                req = bus.MessageRequest()
                req.to = to
                req.command = cmd
                resp = bus_.push(req)
                if resp['error']:
                    print('FAILURE: %s' % resp['message'])
                else:
                    print('RESPONSE:')
                    pp.pprint(resp['data'])
            except Exception,e:
                print str(e)
    print 'STOPPED'

    g.stop()
