"""Fast radial field-of-view envelope, with adaptive fade rejection and inset.

Detection uses sampled luminance profiles, not a learned model. The detected
view boundary is separate from, and never simplifies, annotation vertices.
"""
import numpy as np
from PIL import Image


def detect_view_boundary(path, inset=4, transition=.35):
    with Image.open(path) as image:
        original = image.size
        image = image.convert('RGB')
        image.thumbnail((512, 512))
        light = np.asarray(image).max(axis=2).astype(np.float32)
    h, w = light.shape
    outer = np.concatenate([light[0], light[-1], light[:, 0], light[:, -1]])
    inner = light[h//4:3*h//4, w//4:3*w//4]
    reference = float(np.percentile(inner, 70))
    if reference < 24 or np.mean(outer < reference*.45) < .35:
        return None
    # A robust central location tolerates minor off-centre optics.
    yy, xx = np.nonzero(light > max(18, reference*.5))
    if not len(xx):
        return None
    cx = (np.percentile(xx, 3)+np.percentile(xx, 97))/2
    cy = (np.percentile(yy, 3)+np.percentile(yy, 97))/2
    angles = np.arange(256)*2*np.pi/256
    dx, dy = np.cos(angles), np.sin(angles)
    limit = np.minimum(np.where(dx>=0, (w-1-cx)/np.maximum(dx, 1e-6), cx/np.maximum(-dx, 1e-6)),
                       np.where(dy>=0, (h-1-cy)/np.maximum(dy, 1e-6), cy/np.maximum(-dy, 1e-6)))
    fractions = np.linspace(.12, 1, 192)
    radius = limit[:, None]*fractions
    x = np.clip(np.rint(cx+dx[:, None]*radius).astype(int), 0, w-1)
    y = np.clip(np.rint(cy+dy[:, None]*radius).astype(int), 0, h-1)
    profile = light[y, x]
    local = np.percentile(profile[:, :100], 70, axis=1)
    threshold = np.maximum(18, np.maximum(local, reference*.7)*transition)
    # Last adequately illuminated sample follows the fade transition inward.
    adequate = profile >= threshold[:, None]
    indices = np.max(np.where(adequate, np.arange(192), -1), axis=1)
    radii = radius[np.arange(256), np.maximum(indices, 0)]
    # Angular median rejects narrow dark tissue spokes attached to the padding.
    radii = np.median(np.stack([np.roll(radii, k) for k in range(-6, 7)]), axis=0)
    sx, sy = original[0]/w, original[1]/h
    radii = np.maximum(1, radii - float(inset)/max(sx, sy))
    gy, gx = np.indices((h,w))
    a = (np.arctan2(gy-cy, gx-cx) % (2*np.pi))*256/(2*np.pi)
    boundaries = np.interp(a, np.arange(257), np.r_[radii, radii[0]])
    valid = (gx-cx)**2+(gy-cy)**2 <= boundaries**2
    if not .10 < valid.mean() < .97:
        return None
    edge = np.column_stack(((cx+dx*radii)*sx, (cy+dy*radii)*sy))
    return valid, edge, sx, sy
