import socket
import threading
import signal
import os
import lru


class Server(object):
    def __init__(self, _host, _port, _file):
        """ We set class params, plus we bing socket (interface and port)
        """
        try:
            self.lines_lru = lru.LRU(200)
            self.lines_lru_lock = threading.Lock()
            self.file = _file
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((_host, _port))
            print("Binding to {}:{}".format(_host, _port))
        except Exception as e:
            print(e)

    def listen(self):
        """ Classical approach, one thread per incoming connection
        """
        print("Listening")
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            """
            In CPython, due to the Global Interpreter Lock, only one thread can execute 
            Python code at once (even though certain performance-oriented libraries might 
            overcome this limitation). If you want your application to make better use of 
            the computational resources of multi-core machines, you are advised to use 
            multiprocessing or concurrent.futures.ProcessPoolExecutor. However, threading is 
            still an appropriate model if you want to run multiple I/O-bound tasks simultaneously.
            """
            threading.Thread(target=self.serve_client, args=[client, address]).start()

    def get_line_file(self, line_no):
        print("Fetching line: " + str(line_no))

        # if there is no such line, we will send ERR
        result = 'ERR\r\n'
        try:
            with self.lines_lru_lock:
                result = 'OK\r\n' + self.lines_lru[line_no][:]
                print('We get the line from the buffer, no need to open file')
        except KeyError:
            # open file and seek for the right line
            # I could keep the file open, but this would require more synchronization
            with open(self.file) as f:
                print('We scan the file')
                for i, line in enumerate(f, 1):  # uses f.next, not need to load the whole file into memory
                    if i == line_no:
                        # we found this line in the file, let's butter it
                        result = 'OK\r\n' + line
                        with self.lines_lru_lock:
                            self.lines_lru[i] = line
                        break

        return result.encode()

    def process_commands(self, commands, client):
        """ The method processes a batch of commands from a client, and calls action for each command.
        :param commands: a list oc commands from our client
        :param client: socket to communicate with the client
        :return: True if we want the communication with the client to continue, False otherwise
        """
        for command in commands:
            command = command.rstrip()
            print('Command to process:', command)
            if command.startswith('QUIT'):
                print("Client says QUIT, let's say good bye")
                client.send(b'good bye\n')
                client.close()
                return False
            elif command.startswith('SHUTDOWN'):
                print("Client says SHUTDOWN, let's shutdown the server")
                client.close()
                os.kill(os.getpid(), signal.SIGINT)
                return False
            elif command.startswith('GET '):
                print("Client says GET, let's get to work")
                line_no = int(command.split()[1])
                result = self.get_line_file(line_no)
                client.send(result)
            elif len(command) == 0:
                print("Empty line, this commands batch is over")
            else:
                print("Client says something I don't understand")
                client.send(b"I don't understand you\n")
        return True

    def serve_client(self, client, address):
        """ A method receiving data from client, and spiting lines into separate commands
        :param client: client's socket
        :param address: client's/remote address and port
        :return:
        """
        size = 4096
        print("Serving client: ", address[0], address[1])
        keep_running = True
        while keep_running:
            try:
                # read data from the client
                commands = client.recv(size)
                if commands:
                    try:
                        # decode to string and split by 'new line', every line is a command
                        commands = commands.decode().split('\n')
                        # process all commands
                        keep_running = self.process_commands(commands, client)
                        print(self.lines_lru)
                    # when client try to send some weird characters, we close connection
                    except UnicodeError:
                        print('Non unicode string, end of communication')
                        keep_running = False
                else:
                    keep_running = False
            except Exception as e:
                keep_running = False
                print('Exception', e)
        client.close()
