import getpass
from cis_interface import backwards
from cis_interface.serialize.DefaultSerialize import DefaultSerialize


class PlySerialize(DefaultSerialize):
    r"""Class for serializing/deserializing .ply file formats.

    Args:
        write_header (bool, optional): If True, headers will be added to
            serialized output. Defaults to True.
        newline (str, optional): String that should be used for new lines.
            Defaults to '\n'.

    Attributes:
        write_header (bool): If True, headers will be added to serialized
            output.
        newline (str): String that should be used for new lines.
        default_rgb (list): Default color in RGB that should be used for
            missing colors.

    """

    def __init__(self, *args, **kwargs):
        self.write_header = kwargs.pop('write_header', True)
        self.newline = backwards.bytes2unicode(kwargs.pop('newline', '\n'))
        self.default_rgb = [0, 0, 0]
        super(PlySerialize, self).__init__(*args, **kwargs)

    @property
    def serializer_type(self):
        r"""int: Type of serializer."""
        return 9
        
    @property
    def empty_msg(self):
        r"""obj: Object indicating empty message."""
        return backwards.unicode2bytes('')
            
    def func_serialize(self, args):
        r"""Serialize a message.

        Args:
            args (dict): Dictionary of ply information. Fields include:
                vertices (list): 3D positions of vertices comprising the object.
                faces (list): Indices of 3 or more vertices making up faces.
                vertex_colors (list): RGB values for each of the vertices.
                    If not provided, all vertices will be black.

        Returns:
            bytes, str: Serialized message.

        """
        lines = []
        nvert = len(args.get('vertices', []))
        nface = len(args.get('faces', []))
        # Header
        if self.write_header:
            lines += ['ply',
                      'format ascii 1.0',
                      'comment author %s' % getpass.getuser(),
                      'comment File generated by cis_interface',
                      'element vertex %d' % nvert,
                      'property float x',
                      'property float y',
                      'property float z',
                      'property uchar diffuse_red',
                      'property uchar diffuse_green',
                      'property uchar diffuse_blue',
                      'element face %d' % nface,
                      'property list uchar int vertex_indices',
                      'end_header']
        # Set colors if not provided
        if not args.get('vertex_colors', []):
            args['vertex_colors'] = []
            for v in args.get('vertices', []):
                args['vertex_colors'].append(self.default_rgb)
        # 3D objects
        for i in range(len(args.get('vertices', []))):
            v = args['vertices'][i]
            c = args['vertex_colors'][i]
            entry = tuple(list(v) + list(c))
            lines.append('%f %f %f %d %d %d' % entry)
        for f in args.get('faces', []):
            nv = len(f)
            iline = '%d' % nv
            for v in f:
                iline += ' %d' % v
            lines.append(iline)
        out = self.newline.join(lines)
        return backwards.unicode2bytes(out)

    def func_deserialize(self, msg, nvert=None, nface=None):
        r"""Deserialize a message.

        Args:
            msg (str, bytes): Message to be deserialized.
            nvert (int, optional): Number of vertices expected if the ply
                header is not in the message. Defaults to None.
            nface (int, optional): Number of faces expected if the ply
                header is not in the message. Defaults to None.

        Returns:
            dict: Deserialized .ply information.

        """
        if len(msg) == 0:
            out = self.empty_msg
        else:
            lines = backwards.bytes2unicode(msg).split(self.newline)
            # Split header and body
            headline = 0
            for i in range(len(lines)):
                if 'end_header' in lines[i]:
                    headline = i + 1
                    break
            if headline > 0:
                for i in range(headline):
                    if lines[i].startswith('element vertex'):
                        nvert = int(lines[i].split()[2])
                    elif lines[i].startswith('element face'):
                        nface = int(lines[i].split()[2])
            if (nvert is None) or (nface is None):  # pragma: debug
                raise RuntimeError("Could not locate element definitions.")
            # Get 3D info
            out = dict(vertices=[], faces=[], vertex_colors=[])
            i = headline
            while len(out['vertices']) < nvert:
                values = lines[i].split()
                if len(values) > 0:
                    out['vertices'].append(map(float, values[:3]))
                    if len(values) >= 6:
                        out['vertex_colors'].append(map(int, values[3:]))
                    else:
                        out['vertex_colors'].append(self.default_rgb)
                i += 1
            while len(out['faces']) < nface:
                values = lines[i].split()
                if len(values) > 0:
                    nv = int(values[0])
                    out['faces'].append(map(int, values[1:(nv + 1)]))
                    for x in out['faces'][-1]:
                        assert(x < len(out['vertices']))
                i += 1
        return out
