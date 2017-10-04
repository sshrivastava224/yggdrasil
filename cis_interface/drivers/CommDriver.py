import importlib
from cis_interface.drivers.Driver import Driver
from cis_interface.tools import PSI_MSG_MAX


maxMsgSize = PSI_MSG_MAX
DEBUG_SLEEPS = True


class CommDriver(Driver):
    r"""Base driver for any driver that does communication.

    Args:
        name (str): The name of the message queue that the driver should
            connect to.
        comm (str, optional): The name of a communication class from the
            cis_interface.communication subpackage. Defaults to 'IPCComm'.
        \*\*kwargs: Additional keyword arguments are passed to the comm class.

    Attributes:
        comm_cls (class): Communication class.
        comm (CommBase): Instance of communication class.
        state (str): Description of the last operation performed by the driver.
        numSent (int): The number of messages sent to the queue.
        numReceived (int): The number of messages received from the queue.

    """
    def __init__(self, name, comm='IPCComm', **kwargs):
        super(CommDriver, self).__init__(name)
        self.debug()
        self.state = 'Started'
        self.numSent = 0
        self.numReceived = 0
        mod = importlib.import_module('cis_interface.communication.%s' % comm)
        self.comm_cls = getattr(mod, comm)
        self.comm = self.comm_cls.new_comm(name, dont_open=True, **kwargs)
        self.env[name] = self.comm.address
        self.debug(".env: %s", self.env)

    @property
    def is_valid(self):
        r"""bool: Returns True if the connection is open and the parent class
        is valid."""
        with self.lock:
            return (super(CommDriver, self).is_valid and self.is_open)

    @property
    def is_open(self):
        r"""bool: Returns True if the connection is open."""
        with self.lock:
            return self.comm.is_open

    @property
    def n_msg(self):
        r"""int: The number of messages in the queue."""
        with self.lock:
            return self.comm.n_msg

    @property
    def run(self):
        r"""Open the connection."""
        self.comm.open()

    def graceful_stop(self, timeout=None, **kwargs):
        r"""Stop the CommDriver, first draining the message queue.

        Args:
            timeout (float, optional): Max time that should be waited. Defaults
                to None and is set to attribute timeout. If 0, it will never
                timeout.
            \*\*kwargs: Additional keyword arguments are passed to the parent
                class's graceful_stop method.

        """
        self.debug('.graceful_stop()')
        T = self.start_timeout(timeout)
        try:
            while (self.n_msg > 0) and (not T.is_out):
                if DEBUG_SLEEPS:
                    self.debug('.graceful_stop(): draining %d messages',
                               self.n_msg)
                self.sleep()
        except Exception as e:  # pragma: debug
            self.raise_error(e)
        self.stop_timeout()
        super(CommDriver, self).graceful_stop()
        self.debug('.graceful_stop(): done')

    def close(self):
        r"""Close the queue."""
        self.debug(':close_queue()')
        with self.lock:
            self.comm.close()
        self.debug(':close_queue(): done')
        
    def terminate(self):
        r"""Stop the CommDriver, removing the queue."""
        if self._terminated:
            self.debug(':terminated() Driver already terminated.')
            return
        self.debug(':terminate()')
        self.close()
        super(CommDriver, self).terminate()
        self.debug(':terminate(): done')

    def cleanup(self):
        r"""Ensure that the queues are removed."""
        self.debug(':cleanup()')
        self.close()
        super(CommDriver, self).cleanup()

    def printStatus(self, beg_msg='', end_msg=''):
        r"""Print information on the status of the CommDriver.

        Arguments:
            beg_msg (str, optional): Additional message to print at beginning.
            end_msg (str, optional): Additional message to print at end.

        """
        msg = beg_msg
        msg += '%-30s' % (self.__module__ + '(' + self.name + ')')
        msg += '%-30s' % ('last action: ' + self.state)
        msg += '%-15s' % (str(self.numSent) + ' delivered, ')
        msg += '%-15s' % (str(self.numReceived) + ' accepted, ')
        msg += '%-15s' % (str(self.n_msg) + ' ready')
        msg += end_msg

    def send(self, data):
        r"""Send a message smaller than maxMsgSize.

        Args:
            str: The message to be sent.

        Returns:
            bool: Success or failure of send.

        """
        with self.lock:
            self.state = 'deliver'
            ret = self.comm.send(data)
            if ret:
                self.state = 'delivered'
                self.numSent = self.numSent + 1
            else:
                self.state = 'delivery failed'
        return ret

    def recv(self):
        r"""Receive a message smaller than maxMsgSize.

        Returns:
            tuple (bool, str): The success or failure of receiving and the
                received message.

        """
        with self.lock:
            self.state = 'receiving'
            ret = self.comm.recv()
            if ret[0]:
                self.state = 'received'
                self.numReceived += 1
            else:
                self.state = 'received failed'
        return ret

    def send_nolimit(self, data):
        r"""Send a message larger than maxMsgSize in multiple parts.

        Args:
            str: The message to be sent.

        Returns:
            bool: Success or failure of send.

        """
        ret = self.comm.send_nolimit(data)
        return ret

    def recv_nolimit(self):
        r"""Receive a message larger than maxMsgSize in multiple parts.

        Returns:
            tuple (bool, str): The success or failure of receiving and the
                received message.

        """
        ret = self.comm.recv_nolimit()
        return ret
