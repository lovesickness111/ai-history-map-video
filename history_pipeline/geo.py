"""Small Blender-independent readers for preprocessed metric GIS data."""
import math


def sample_height(grid,x,y):
    """Bilinear metric Z; row zero is north, columns run east."""
    col=(x-grid['x0'])/grid['dx']
    row=(y-grid['y0'])/grid['dy']
    col=max(0,min(grid['cols']-1.000001,col))
    row=max(0,min(grid['rows']-1.000001,row))
    c,r=int(col),int(row)
    u,v=col-c,row-r
    z=grid['heights']
    return ((1-v)*((1-u)*z[r][c]+u*z[r][c+1])
            +v*((1-u)*z[r+1][c]+u*z[r+1][c+1]))


def point_in_ring(x,y,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside=not inside
    return inside


def point_segment_distance(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy or 1)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
