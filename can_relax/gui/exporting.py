"""Figure serialization shared by previews and downloads."""
import io
import numpy as np
from PIL import Image

MIME_TYPES = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
              'bmp': 'image/bmp', 'tiff': 'image/tiff', 'pdf': 'application/pdf',
              'svg': 'image/svg+xml'}


def figure_bytes(fig, fmt, dpi=300, colorspace='RGB', tight=False):
    """Render at the requested resolution; never disguise a different format.

    CMYK PDF is rasterized. RGB PDF/SVG retain vector content. Limit raster
    allocation before rendering, including the tight bounding box when requested.
    """
    fmt = fmt.lower()
    if fmt not in MIME_TYPES:
        raise ValueError(f'Unsupported export format: {fmt}')
    cmyk = colorspace.startswith('CMYK')
    if cmyk and fmt not in ('jpg', 'jpeg', 'tiff', 'pdf'):
        raise ValueError('CMYK requires JPEG, TIFF or PDF. Choose RGB for PNG, BMP or SVG.')
    if not np.isfinite(dpi) or dpi <= 0:
        raise ValueError('DPI must be finite and positive.')
    raster = cmyk or fmt not in ('pdf', 'svg')
    if raster:
        size = fig.get_size_inches()
        if tight:
            fig.canvas.draw()
            box = fig.get_tightbbox(fig.canvas.get_renderer())
            size = np.array([box.width, box.height]) + .2
        pixels = size * dpi
        if not np.all(np.isfinite(pixels)) or np.prod(pixels) > 40_000_000:
            raise ValueError('Export exceeds 40 megapixels. Reduce figure dimensions or DPI.')
    options = {'bbox_inches': 'tight'} if tight else {}
    output = io.BytesIO()
    if not cmyk and fmt not in ('bmp', 'tiff', 'jpg', 'jpeg'):
        fig.savefig(output, format=fmt, dpi=dpi, **options)
    else:
        png = io.BytesIO()
        fig.savefig(png, format='png', dpi=dpi, facecolor='white', **options)
        png.seek(0)
        with Image.open(png) as source:
            rgb = Image.new('RGB', source.size, 'white')
            rgba = source.convert('RGBA')
            rgb.paste(rgba, mask=rgba.getchannel('A'))
            converted = rgb.convert('CMYK') if cmyk else rgb
            save_options = {'dpi': (dpi, dpi)}
            if fmt in ('jpg', 'jpeg'):
                save_options['quality'] = 95
            if fmt == 'tiff':
                save_options['compression'] = 'tiff_lzw'
            converted.save(output, format='JPEG' if fmt in ('jpg', 'jpeg') else fmt.upper(), **save_options)
    return output.getvalue()
