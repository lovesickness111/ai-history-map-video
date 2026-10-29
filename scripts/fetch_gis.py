"""Fetch public DEM + map vectors; crop exactly and export Blender-ready GIS.

Run in the host GIS venv, never in Blender's Python. No API key is required.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import ssl
import sys
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image,ImageDraw
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import reproject,Resampling,transform_bounds
from pyproj import Transformer,Geod
from shapely.geometry import shape,Polygon,LineString,Point,box,mapping
from shapely.ops import transform,triangulate,unary_union
from shapely import constrained_delaunay_triangles
from history_pipeline.geo import sample_height

AGENT='HanoiHistoryPipeline/1.0 (read-only public GIS fetch)'
try:
    import certifi as _certifi
    _SSL_CTX=ssl.create_default_context(cafile=_certifi.where())
except ImportError:
    _SSL_CTX=ssl.create_default_context()
# _SSL_CTX always verifies TLS; certifi provides an up-to-date CA bundle on Windows.


def write_json(path,data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')


def download(url,path):
    if path.is_file() and path.stat().st_size:
        return path
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.part')
    print(f'Download: {url}',flush=True)
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':AGENT})
            with urllib.request.urlopen(req,timeout=90,context=_SSL_CTX) as source,temp.open('wb') as target:
                while chunk:=source.read(1024*1024):
                    target.write(chunk)
            temp.replace(path)
            return path
        except OSError:
            if attempt==2: raise
            time.sleep(2**attempt)


def tile_name(lat,lon):
    return f"Copernicus_DSM_COG_10_{'N' if lat>=0 else 'S'}{abs(lat):02d}_00_{'E' if lon>=0 else 'W'}{abs(lon):03d}_00_DEM"


def encode_height16(values,valid):
    low,high=float(values[valid].min()),float(values[valid].max())
    scale=(high-low)/65534 if high>low else .001
    offset=low-scale
    encoded=np.zeros(values.shape,dtype=np.uint16)
    encoded[valid]=np.clip(np.rint((values[valid]-offset)/scale),1,65535).astype(np.uint16)
    return encoded,{'scale_m_per_code':scale,'offset_m':offset,'nodata_code':0,'min_m':low,'max_m':high}


def fetch_dem(config,out,cache):
    west,south,east,north=config['bbox_wgs84']
    crop_id=hashlib.sha256(json.dumps(config['bbox_wgs84']).encode()).hexdigest()[:14]
    crop=cache/f'dem_window_{crop_id}.tif'
    sources_file=cache/f'dem_window_{crop_id}.json'
    if crop.exists() and sources_file.exists():
        with rasterio.open(crop) as dataset:
            source,source_transform,src_crs=dataset.read(),dataset.transform,dataset.crs
        sources=json.loads(sources_file.read_text(encoding='utf-8'))
    else:
        sources=[]
        tiles=[]
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
            try:
                for lat in range(math.floor(south),math.ceil(north)):
                    for lon in range(math.floor(west),math.ceil(east)):
                        name=tile_name(lat,lon)
                        url=f'https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif'
                        print(f'Read COG window over HTTP Range: {name}',flush=True)
                        tiles.append(rasterio.open('/vsicurl/'+url))
                        sources.append({'url':url,'access':'HTTP Range; only intersecting COG blocks'})
                pad=2/3600
                source,source_transform=merge(tiles,bounds=(west-pad,south-pad,east+pad,north+pad),nodata=-9999)
                src_crs=tiles[0].crs
            finally:
                for tile in tiles: tile.close()
        with rasterio.open(crop,'w',driver='GTiff',width=source.shape[2],height=source.shape[1],count=1,
                           dtype='float32',crs=src_crs,transform=source_transform,nodata=-9999,compress='deflate') as dst:
            dst.write(source)
        with crop.open('rb') as handle:
            digest=hashlib.file_digest(handle,'sha256').hexdigest()
        for item in sources: item['cached_crop_sha256']=digest
        write_json(sources_file,sources)
    resolution=config['resolution_m']
    projected_bounds=transform_bounds('EPSG:4326',config['projected_crs'],west,south,east,north,densify_pts=21)
    left,bottom,right,top=projected_bounds
    width=max(2,math.ceil((right-left)/resolution))
    height=max(2,math.ceil((top-bottom)/resolution))
    projected_transform=from_bounds(left,bottom,right,top,width,height)
    projected=np.full((height,width),-9999,dtype=np.float32)
    reproject(source[0],projected,src_transform=source_transform,src_crs=src_crs,
              dst_transform=projected_transform,dst_crs=config['projected_crs'],
              src_nodata=-9999,dst_nodata=-9999,resampling=Resampling.bilinear)
    valid=np.isfinite(projected)&(projected!=-9999)
    if not valid.all():
        raise ValueError(f'DEM has {np.count_nonzero(~valid)} nodata cells inside AOI; no silent zero fill')
    # Geographic deliverable has exactly the user's WGS84 bbox, including subpixels.
    geographic=np.full((height,width),-9999,dtype=np.float32)
    geographic_transform=from_bounds(west,south,east,north,width,height)
    reproject(source[0],geographic,src_transform=source_transform,src_crs=src_crs,
              dst_transform=geographic_transform,dst_crs='EPSG:4326',src_nodata=-9999,
              dst_nodata=-9999,resampling=Resampling.bilinear)
    for filename,array,crs,affine in (('dem_wgs84.tif',geographic,'EPSG:4326',geographic_transform),
                                    ('dem_utm_float.tif',projected,config['projected_crs'],projected_transform)):
        with rasterio.open(out/filename,'w',driver='GTiff',width=width,height=height,count=1,
                           dtype='float32',crs=crs,transform=affine,nodata=-9999,compress='deflate') as dst:
            dst.write(array,1)
    encoded,encoding=encode_height16(projected,valid)
    with rasterio.open(out/'heightmap_16.tif','w',driver='GTiff',width=width,height=height,count=1,
                       dtype='uint16',crs=config['projected_crs'],transform=projected_transform,
                       nodata=0,compress='deflate') as dst:
        dst.write(encoded,1)
        dst.scales=(encoding['scale_m_per_code'],)
        dst.offsets=(encoding['offset_m'],)
        dst.update_tags(HEIGHT_UNITS='metres',SOURCE='Copernicus GLO-30 DSM')
    Image.fromarray(encoded).save(out/'heightmap_16.png')
    a=projected_transform
    (out/'heightmap_16.pgw').write_text('\n'.join(map(str,(a.a,a.d,a.b,a.e,a.c+a.a/2,a.f+a.e/2)))+'\n')
    # Preserve the raw DSM. A documented median reduces rooftop spikes for display.
    pad=np.pad(projected,2,mode='edge')
    ground=np.median(np.lib.stride_tricks.sliding_window_view(pad,(5,5)),axis=(-1,-2)).astype(np.float32)
    origin=[(left+right)/2,(bottom+top)/2]
    z_origin=float(np.median(ground))
    units=config['meters_per_unit']
    grid={'cols':width,'rows':height,'x0':(a.c+a.a/2-origin[0])/units,
          'y0':(a.f+a.e/2-origin[1])/units,'dx':a.a/units,'dy':a.e/units,
          'heights':((ground-z_origin)*config['vertical_exaggeration']/units).tolist()}
    meta={'sources':sources,'bbox_wgs84':[west,south,east,north],
          'bounds_projected_m':list(projected_bounds),'projected_crs':config['projected_crs'],
          'origin_projected_m':origin,'z_origin_m':z_origin,'meters_per_unit':units,
          'native_resolution_m_approx':30,'grid_resolution_m':[a.a,-a.e],
          'heightmap_encoding':encoding,'terrain_filter':'5x5 median for display only; raw DSM preserved',
          'vertical_exaggeration':config['vertical_exaggeration'],
          'vertical_datum':'Copernicus DSM orthometric height, EGM2008; not ellipsoidal GNSS height'}
    return grid,meta


def fetch_osm(bbox,cache,building_bbox=None):
    building_bbox=building_bbox or bbox
    west,south,east,north=bbox
    bounds=f'({south},{west},{north},{east})'
    queries=[f'[out:json][timeout:55];way[highway~"^(primary|secondary|tertiary|residential|unclassified|living_street|pedestrian)$"]{bounds};out geom;',
             f'[out:json][timeout:55];(way[natural=water]{bounds};way[waterway=riverbank]{bounds};way[waterway=river]{bounds};);out geom;']
    bw,bs,be,bn=building_bbox
    for iy in range(2):
        for ix in range(2):
            x0,x1=bw+(be-bw)*ix/2,bw+(be-bw)*(ix+1)/2
            y0,y1=bs+(bn-bs)*iy/2,bs+(bn-bs)*(iy+1)/2
            queries.append(f'[out:json][timeout:55];way[building]({y0},{x0},{y1},{x1});out geom;')
    all_elements={}
    endpoints=[]
    timestamp=None
    for index,query in enumerate(queries):
        data=fetch_osm_query(query,cache)
        print(f'OSM layer {index+1}/{len(queries)}: {len(data["elements"])} elements',flush=True)
        all_elements.update({(e['type'],e['id']):e for e in data['elements']})
        endpoints.append(data['endpoint'])
        timestamp=data.get('osm3s',{}).get('timestamp_osm_base')
    return {'elements':list(all_elements.values()),'endpoint':','.join(sorted(set(endpoints))),
            'osm3s':{'timestamp_osm_base':timestamp}}


def fetch_osm_query(query,cache):
    digest=hashlib.sha256(query.encode()).hexdigest()[:14]
    path=cache/f'osm_{digest}.json'
    if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    errors=[]
    endpoints=(
        'https://overpass.osm.ch/api/interpreter',
        'https://overpass.private.coffee/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass-api.de/api/interpreter',
        'https://overpass.openstreetmap.ru/api/interpreter',
    )
    for attempt,host in enumerate(endpoints):
        try:
            print(f'Fetch map vectors: {host}',flush=True)
            req=urllib.request.Request(host,data=urllib.parse.urlencode({'data':query}).encode(),
                                       headers={'User-Agent':AGENT})
            with urllib.request.urlopen(req,timeout=90,context=_SSL_CTX) as response:
                data=json.load(response)
            if data.get('remark'): raise ValueError(data['remark'])
            data['endpoint']=host
            write_json(path,data)
            return data
        except (OSError,ValueError) as exc:
            errors.append(f'{host}: {exc}')
            if attempt<len(endpoints)-1:
                time.sleep(2)
    raise RuntimeError('Cannot fetch OSM vectors; no invented geographic fallback. '+ '; '.join(errors))


def polygons(geometry):
    if geometry.is_empty: return []
    if geometry.geom_type=='Polygon': return [geometry]
    if geometry.geom_type in ('MultiPolygon','GeometryCollection'):
        return [p for child in geometry.geoms for p in polygons(child)]
    return []


def export_vectors(osm,config,project,meta):
    units=meta['meters_per_unit']
    ox,oy=meta['origin_projected_m']
    def local(lon,lat,z=None):
        x,y=project.transform(lon,lat)
        return (np.asarray(x)-ox)/units,(np.asarray(y)-oy)/units
    aoi=box(*meta['bounds_projected_m'])
    aoi=transform(lambda x,y,z=None:((np.asarray(x)-ox)/units,(np.asarray(y)-oy)/units),aoi)
    roads,water,buildings=[],[],[]
    source_features=[]
    for item in osm.get('elements',[]):
        tags=item.get('tags',{})
        geo=item.get('geometry',[])
        if item['type']=='relation':
            # Assemble outer/inner member rings, preserving islands in lakes/rivers.
            from shapely.ops import polygonize
            outer,inner=[],[]
            for member in item.get('members',[]):
                coords=[(p['lon'],p['lat']) for p in member.get('geometry',[])]
                if len(coords)>1:
                    (inner if member.get('role')=='inner' else outer).append(LineString(coords))
            if not outer: continue
            outer_polys=list(polygonize(unary_union(outer)))
            inner_polys=list(polygonize(unary_union(inner))) if inner else []
            geometry=unary_union(outer_polys)
            if inner_polys: geometry=geometry.difference(unary_union(inner_polys))
        else:
            coords=[(p['lon'],p['lat']) for p in geo]
            if len(coords)<2: continue
            if 'highway' in tags or tags.get('waterway')=='river':
                geometry=LineString(coords)
            elif len(coords)>3 and coords[0]==coords[-1]:
                geometry=Polygon(coords)
            else: continue
        if geometry.is_empty: continue
        if not geometry.is_valid: geometry=geometry.buffer(0)
        source_features.append({'type':'Feature','properties':{'osm_id':item['id'],**tags},'geometry':mapping(geometry)})
        geographic=geometry
        geometry=transform(local,geometry).intersection(aoi)
        if 'highway' in tags:
            width_m={'primary':12,'secondary':10,'tertiary':8,'residential':5,'pedestrian':5,'unclassified':5,'living_street':4}.get(tags['highway'],5)
            lines=[geometry] if geometry.geom_type=='LineString' else list(getattr(geometry,'geoms',[]))
            for line in lines:
                if line.geom_type=='LineString' and line.length>.15:
                    roads.append({'id':item['id'],'name':tags.get('name',''),'width':width_m/units,
                                  'points':[list(p) for p in line.simplify(.12).coords]})
        elif tags.get('natural')=='water' or tags.get('waterway') in ('riverbank','river'):
            if geometry.geom_type=='LineString':
                width=tags.get('width','200')
                try: width=float(width)
                except ValueError: width=200
                geometry=geometry.buffer(width/(2*units))
                tags['boundary_note']='Mapped river centerline buffered by tagged width or estimated 200 m'
            for polygon in polygons(geometry):
                water.append({'id':item['id'],'name':tags.get('name',''),
                              'outer':[list(p) for p in polygon.exterior.coords],
                              'holes':[[list(p) for p in ring.coords] for ring in polygon.interiors]})
        elif 'building' in tags:
            for polygon in polygons(geometry):
                if 15<=polygon.area*units**2<=500:
                    buildings.append((item['id'],polygon,tags))
    return roads,water,buildings,{'type':'FeatureCollection','features':source_features,'attribution':'© OpenStreetMap contributors, ODbL 1.0'}


def create_houses(config,roads,water,buildings,landmarks,grid,project,meta):
    rng=random.Random(config['town_seed'])
    units=meta['meters_per_unit']
    ox,oy=meta['origin_projected_m']
    west,south,east,north=config['old_quarter_bbox']
    corners=[project.transform(lon,lat) for lon,lat in ((west,south),(east,north))]
    quarter=box((corners[0][0]-ox)/units,(corners[0][1]-oy)/units,
                (corners[1][0]-ox)/units,(corners[1][1]-oy)/units)
    water_geom=unary_union([Polygon(w['outer'],w['holes']) for w in water])
    roads_geom=unary_union([LineString(r['points']).buffer(r['width']/2+.15) for r in roads])
    reserved=unary_union([Point(*landmark['position'][:2]).buffer(7 if landmark['id']=='flag_tower' else 3) for landmark in landmarks])
    forbidden=unary_union([water_geom,roads_geom,reserved])
    candidates=[b for b in buildings if quarter.covers(b[1].representative_point())]
    rng.shuffle(candidates)
    selected=[]
    occupied=[]
    spatial={}
    for osm_id,polygon,tags in candidates:
        if len(selected)>=config['max_houses']: break
        rectangle=polygon.minimum_rotated_rectangle
        coords=list(rectangle.exterior.coords)
        lengths=[math.dist(coords[i],coords[i+1]) for i in range(4)]
        width,depth=min(lengths[:2]),max(lengths[:2])
        if width<.25 or depth<.4: continue
        width=min(.85,max(.35,width*.78))
        depth=min(1.7,max(.55,depth*.78))
        width=max(v for v in (.35,.5,.65,.8) if v<=width)
        depth=max(v for v in (.55,.8,1.05,1.3,1.55) if v<=depth)
        center=polygon.centroid
        edge=0 if lengths[0]>=lengths[1] else 1
        # House long axis is local Y.
        angle=math.atan2(coords[edge+1][1]-coords[edge][1],coords[edge+1][0]-coords[edge][0])-math.pi/2
        from shapely import affinity
        footprint=box(-width/2-.06,-depth/2-.11,width/2+.06,depth/2+.11)
        footprint=affinity.rotate(footprint,angle,origin=(0,0),use_radians=True)
        footprint=affinity.translate(footprint,center.x,center.y)
        if footprint.intersects(forbidden): continue
        x0,y0,x1,y1=footprint.bounds
        cells=[(gx,gy) for gx in range(math.floor(x0/2),math.floor(x1/2)+1)
               for gy in range(math.floor(y0/2),math.floor(y1/2)+1)]
        neighbors={i for cell in cells for i in spatial.get(cell,())}
        if any(footprint.intersects(occupied[i]) for i in neighbors): continue
        for cell in cells: spatial.setdefault(cell,[]).append(len(occupied))
        occupied.append(footprint)
        selected.append({'id':f'house_{len(selected)+1:04d}','model_id':'nha_co','seed':config['town_seed']+len(selected),
                         'position':[center.x,center.y,sample_height(grid,center.x,center.y)],
                         'rotation':[0,0,math.degrees(angle)],'scale':[1,1,.7],
                         'params':{'width':round(width,3),'depth':round(depth,3),
                                   'height':rng.choice((.55,.7,.85)),'variant':rng.randrange(5)},
                         'osm_id':osm_id,'placement_source':'OpenStreetMap building footprint; historical facade is illustrative'})
    if not selected: raise ValueError('No safe OSM building footprints found in the old-quarter AOI')
    rng.shuffle(selected)
    for i,item in enumerate(selected):
        wave=min(2,i*3//len(selected))
        within=i-wave*len(selected)//3
        offset=min(30,round(within*30/max(1,len(selected)//3-1)))
        item.update(start_frame=(241,421,781)[wave]+offset,end_frame=(241,421,781)[wave]+offset+24)
    return selected


def country_overview(config,meta,cache,out):
    url='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson'
    path=download(url,cache/'ne_10m_countries.geojson')
    countries=json.loads(path.read_text(encoding='utf-8'))['features']
    feature=next(f for f in countries if f['properties'].get('ADM0_A3')=='VNM')
    geographic=shape(feature['geometry'])
    project=Transformer.from_crs('EPSG:4326',meta['projected_crs'],always_xy=True)
    inverse=Transformer.from_crs(meta['projected_crs'],'EPSG:4326',always_xy=True)
    ox,oy=meta['origin_projected_m']
    units=meta['meters_per_unit']
    country=transform(project.transform,geographic).simplify(350,preserve_topology=True)
    # Hole shares the exact projected bounds of the high-resolution local patch.
    country=country.difference(box(*meta['bounds_projected_m']))
    triangles=list(constrained_delaunay_triangles(country).geoms)
    refined=[]
    pending=[list(t.exterior.coords)[:3] for t in triangles]
    while pending:
        p=pending.pop()
        lengths=[math.dist(p[i],p[(i+1)%3]) for i in range(3)]
        edge=max(range(3),key=lambda i:lengths[i])
        if lengths[edge]>35000 and len(refined)+len(pending)<45000:
            a,b,c=p[edge],p[(edge+1)%3],p[(edge+2)%3]
            middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
            pending.extend(((a,middle,c),(middle,b,c)))
        else: refined.append(p)
    tiles={}
    def terrain(lon,lat):
        zoom=6
        n=2**zoom
        x=(lon+180)/360*n
        y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
        tx,ty=math.floor(x),math.floor(y)
        if (tx,ty) not in tiles:
            file=download(f'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{zoom}/{tx}/{ty}.png',cache/f'terrarium_{zoom}_{tx}_{ty}.png')
            rgb=np.asarray(Image.open(file).convert('RGB'),dtype=np.float64)
            tiles[tx,ty]=rgb[:,:,0]*256+rgb[:,:,1]+rgb[:,:,2]/256-32768
        return float(tiles[tx,ty][min(255,int((y-ty)*256)),min(255,int((x-tx)*256))])
    vertices,faces,colors=[],[],[]
    lookup={}
    for points in refined:
        face=[]
        for x,y in points:
            key=(round(x,3),round(y,3))
            if key not in lookup:
                lon,lat=inverse.transform(x,y)
                h=max(0,terrain(lon,lat))
                lookup[key]=len(vertices)
                vertices.append([(x-ox)/units,(y-oy)/units,(h-meta['z_origin_m'])/units])
                t=min(1,h/2500)
                colors.append([.18+.34*t,.34+.05*t,.15+.20*t,1])
            face.append(lookup[key])
        # Force upward winding after projection.
        a,b,c=[vertices[i] for i in face]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0: face.reverse()
        faces.append(face)
    borders=[]
    for poly in polygons(transform(project.transform,geographic).simplify(350)):
        borders.append([[(x-ox)/units,(y-oy)/units] for x,y in poly.exterior.coords])
    write_json(out/'vietnam_boundary.geojson',{'type':'FeatureCollection','features':[feature]})
    return {'vertices':vertices,'faces':faces,'colors':colors,'borders':borders,
            'source':url,'elevation_source':'https://registry.opendata.aws/terrain-tiles/',
            'license':'Natural Earth public domain; Terrain Tiles attribution in ATTRIBUTION.txt',
            'bounds_scene':[(country.bounds[0]-ox)/units,(country.bounds[1]-oy)/units,
                            (country.bounds[2]-ox)/units,(country.bounds[3]-oy)/units]}


def preview_map(scene,out):
    width,height=1400,1100
    image=Image.new('RGB',(width,height),'#e0dfd1')
    draw=ImageDraw.Draw(image)
    grid=scene['grid']
    left=grid['x0']-grid['dx']/2
    right=left+grid['cols']*grid['dx']
    top=grid['y0']-grid['dy']/2
    bottom=top+grid['rows']*grid['dy']
    scale=min((width-100)/(right-left),(height-120)/(top-bottom))
    def point(p): return (50+(p[0]-left)*scale,60+(top-p[1])*scale)
    for water in scene['water']:
        draw.polygon([point(p) for p in water['outer']],fill='#497d83')
        for hole in water['holes']: draw.polygon([point(p) for p in hole],fill='#d5d3bc')
    for road in scene['roads']:
        draw.line([point(p) for p in road['points']],fill='#a89e85',width=max(1,round(road['width']*scale)))
    for house in scene['town_instances']:
        x,y=point(house['position'])
        draw.rectangle((x-1,y-1,x+1,y+1),fill='#955a43')
    for landmark in scene['landmarks']:
        x,y=point(landmark['position'])
        draw.ellipse((x-7,y-7,x+7,y+7),fill='#dc3429',outline='white',width=2)
        draw.text((x+10,y-14),landmark['id'],fill='#101820')
    draw.text((50,20),'N ↑   WGS84 → UTM 48N → local metres / 10',fill='#101820')
    image.save(out/'map_check.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'data'/'hanoi_gis.json')
    parser.add_argument('--output',type=Path,default=ROOT/'data'/'gis'/'hanoi')
    parser.add_argument('--bbox',nargs=4,type=float,metavar=('WEST','SOUTH','EAST','NORTH'))
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    if args.bbox: config['bbox_wgs84']=args.bbox
    west,south,east,north=config['bbox_wgs84']
    if not (-180<west<east<180 and -80<south<north<84 and east-west<1 and north-south<1):
        raise ValueError('Use a valid local bbox less than one degree per axis')
    if config['resolution_m']<10 or config['meters_per_unit']<=0 or config['vertical_exaggeration']<=0:
        raise ValueError('Invalid resolution, scene scale or vertical exaggeration')
    if any(not (west<=p['lon']<=east and south<=p['lat']<=north) for p in config['landmarks']):
        raise ValueError('A requested landmark falls outside the bbox')
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'data'/'gis_cache'
    cache.mkdir(exist_ok=True)
    grid,meta=fetch_dem(config,out,cache)
    project=Transformer.from_crs('EPSG:4326',meta['projected_crs'],always_xy=True)
    landmarks=[]
    for landmark in config['landmarks']:
        easting,northing=project.transform(landmark['lon'],landmark['lat'])
        x=(easting-meta['origin_projected_m'][0])/meta['meters_per_unit']
        y=(northing-meta['origin_projected_m'][1])/meta['meters_per_unit']
        landmarks.append({**landmark,'position':[x,y,sample_height(grid,x,y)],
                          'projected_m':[easting,northing]})
    osm=fetch_osm(config['bbox_wgs84'],cache,config['old_quarter_bbox'])
    roads,water,buildings,geojson=export_vectors(osm,config,project,meta)
    write_json(out/'map_vectors.geojson',geojson)
    houses=create_houses(config,roads,water,buildings,landmarks,grid,project,meta)
    print(f'OSM: {len(roads)} road segments, {len(water)} water polygons, {len(houses)} building placements',flush=True)
    overview=country_overview(config,meta,cache,out)
    source_features=[{'type':'Feature','geometry':{'type':'Point','coordinates':[p['lon'],p['lat']]},
                      'properties':{k:v for k,v in p.items() if k not in ('lon','lat')}} for p in landmarks]
    write_json(out/'landmarks.geojson',{'type':'FeatureCollection','features':source_features})
    distance=math.dist(landmarks[0]['projected_m'],landmarks[1]['projected_m'])
    geodesic=Geod(ellps='WGS84').inv(landmarks[0]['lon'],landmarks[0]['lat'],landmarks[1]['lon'],landmarks[1]['lat'])[2]
    if abs(distance/geodesic-1)>.001: raise ValueError('Coordinate transform fails distance sanity check')
    meta.update(retrieved_utc=datetime.now(timezone.utc).isoformat(),
                landmark_distance_m=distance,geodesic_landmark_distance_m=geodesic,
                historical_note=config['historical_note'],osm_attribution='© OpenStreetMap contributors, ODbL 1.0',
                osm_endpoint=osm['endpoint'],osm_timestamp=osm.get('osm3s',{}).get('timestamp_osm_base'),
                intro=config['intro'],counts={'houses':len(houses),'roads':len(roads),'water':len(water)})
    meta['layout_sha256']=hashlib.sha256(json.dumps(houses,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    meta['layout_validation']='All selected, oriented roof footprints checked against every occupied footprint, mapped roads, water and landmark buffers'
    for w in water:
        poly=Polygon(w['outer'],w['holes'])
        tris=[]
        for t in constrained_delaunay_triangles(poly).geoms:
            pts=[list(p) for p in list(t.exterior.coords)[:3]]
            if (pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[1][1]-pts[0][1])*(pts[2][0]-pts[0][0])<0:
                pts=[pts[0],pts[2],pts[1]]
            tris.append(pts)
        w['triangles']=tris
        w['level_z']=float(np.percentile([sample_height(grid,*p) for p in w['outer']],10))
    scene={'schema_version':1,'metadata':meta,'grid':grid,'landmarks':landmarks,
           'roads':roads,'water':water,'town_instances':houses,'country':overview}
    write_json(out/'scene.json',scene)
    write_json(out/'manifest.json',meta)
    (out/'ATTRIBUTION.txt').write_text('Copernicus GLO-30 DSM: https://registry.opendata.aws/copernicus-dem/\n'
        'Copernicus licence: https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model\n'
        'Map data © OpenStreetMap contributors, ODbL: https://www.openstreetmap.org/copyright\n'
        'Country outline: Natural Earth, public domain: https://www.naturalearthdata.com/\n'
        'Overview elevation: Terrain Tiles / Mapzen: https://github.com/tilezen/joerd/blob/master/docs/attribution.md\n'
        'Landmark coordinates: Wikidata CC0; individual URLs in landmarks.geojson\n',encoding='utf-8')
    preview_map(scene,out)
    print(f'GIS prepared: {out}; landmark separation {distance:.1f} m',flush=True)


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    main()
