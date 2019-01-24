from cis_interface import backwards  # , platform
from cis_interface.serialize import register_serializer
from cis_interface.serialize.PlySerialize import PlySerialize
from cis_interface.metaschema.datatypes.ObjMetaschemaType import ObjDict


@register_serializer
class ObjSerialize(PlySerialize):
    r"""Class for serializing/deserializing .obj file formats. Reader
    adapted from https://www.pygame.org/wiki/OBJFileLoader."""

    _seritype = 'obj'
    _default_type = {'type': 'obj'}

    def func_serialize(self, args):
        r"""Serialize a message.

        Args:
            args: List of arguments to be formatted or numpy array to be
                serialized.

        Returns:
            bytes, str: Serialized message.

        """
        return backwards.as_bytes(self.datatype.encode_data(args, self.typedef))

    def func_deserialize(self, msg):
        r"""Deserialize a message.

        Args:
            msg: Message to be deserialized.

        Returns:
            obj: Deserialized message.

        """
        return ObjDict(self.datatype.decode_data(backwards.as_str(msg),
                                                 self.typedef))

    @classmethod
    def get_testing_options(cls):
        r"""Method to return a dictionary of testing options for this class.

        Returns:
            dict: Dictionary of variables to use for testing. Key/value pairs:
                kwargs (dict): Keyword arguments for comms tested with the
                    provided content.
                empty (object): Object produced from deserializing an empty
                    message.
                objects (list): List of objects to be serialized/deserialized.
                extra_kwargs (dict): Extra keyword arguments not used to
                    construct type definition.
                typedef (dict): Type definition resulting from the supplied
                    kwargs.
                dtype (np.dtype): Numpy data types that is consistent with the
                    determined type definition.

        """
        out = super(ObjSerialize, cls).get_testing_options()
        obj = ObjDict({'vertices': [{'x': float(0), 'y': float(0), 'z': float(0)},
                                    {'x': float(0), 'y': float(0), 'z': float(1)},
                                    {'x': float(0), 'y': float(1), 'z': float(1)}],
                       'faces': [[{'vertex_index': int(0)},
                                  {'vertex_index': int(1)},
                                  {'vertex_index': int(2)}]]})
        out['objects'] = [obj, obj]
        out['contents'] = (b'# Author cis_auto\n'
                           + b'# Generated by cis_interface\n\n'
                           + b'v 0.0000 0.0000 0.0000\n'
                           + b'v 0.0000 0.0000 1.0000\n'
                           + b'v 0.0000 1.0000 1.0000\n'
                           + b'v 0.0000 0.0000 0.0000\n'
                           + b'v 0.0000 0.0000 1.0000\n'
                           + b'v 0.0000 1.0000 1.0000\n'
                           + b'f 1// 2// 3//\n'
                           + b'f 4// 5// 6//\n')
        # out['contents'] = out['contents'].replace(b'\n', platform._newline)
        return out
