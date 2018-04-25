from cis_interface.drivers.FileOutputDriver import FileOutputDriver


class AsciiMapOutputDriver(FileOutputDriver):
    r"""Class that writes received messages to a ASCII map file.

    Args:
        name (str): Name of the queue that messages should be sent to.
        args (str): Path to the file that messages should be read from.
        **kwargs: Additional keyword arguments are passed to the parent class.

    """
    def __init__(self, name, args, **kwargs):
        icomm_kws = kwargs.get('icomm_kws', {})
        icomm_kws.setdefault('serializer_type', 7)
        ocomm_kws = kwargs.get('ocomm_kws', {})
        ocomm_kws.setdefault('comm', 'AsciiMapComm')
        kwargs['icomm_kws'] = icomm_kws
        kwargs['ocomm_kws'] = ocomm_kws
        super(AsciiMapOutputDriver, self).__init__(name, args, **kwargs)
        self.debug('(%s)', args)
