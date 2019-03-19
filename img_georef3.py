import sys, os, csv, linecache
from math import atan, cos, sin, radians, sqrt, degrees
from tqdm import tqdm
try:
    from osgeo import ogr, osr, gdal
    from wand.display import display
    from wand.image import Image
except:
    sys.exit('ERROR: cannot find GDAL/OGR and/or Wand modules')

print("#########################################################")
print("#####  This script depends on GDAL and ImageMagick  #####")
print("#####  It is best to run in a Python virtualenv     #####")
print("#####  The script is written in Python 3.5.1        #####")
print("#####  by Nate Currit, currit@txstate.edu           #####")
print("#########################################################")
print()

path_to_images = "/home/nate/Documents/Research/Guatemala/photos/2015/PNLT/"

# http://spatialreference.org/ref/sr-org/6866/, epsg.io doesn't define it.
wkt_as_html = 'PROJCS["GTM",\
    GEOGCS["GCS_WGS_1984",\
        DATUM["D_WGS_1984",\
            SPHEROID["WGS_1984",6378137.0,298.257223563]],\
        PRIMEM["Greenwich",0.0],\
        UNIT["Degree",0.0174532925199433]],\
    PROJECTION["Transverse_Mercator"],\
    PARAMETER["False_Easting",500000.0],\
    PARAMETER["False_Northing",0.0],\
    PARAMETER["Central_Meridian",-90.5],\
    PARAMETER["Scale_Factor",0.9998],\
    PARAMETER["Latitude_Of_Origin",0.0],\
    UNIT["Meter",1.0]]'

ogc_wkt = 'PROJCS["GTM",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-90.5],PARAMETER["Scale_Factor",0.9998],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

proj4 = '+proj=tmerc +lat_0=0 +lon_0=-90.5 +k=0.9998 +x_0=500000 +y_0=0 +ellps=WGS84 +units=m +no_defs'

###############################################################
##### User sets the following parameters prior to running #####
###############################################################
crop_width = 1500
crop_height = 1000
x_shift = 0 # -77.32
y_shift = 0 # 16.71
x_resolution = 0.16 # 'rough' pixel spatial resolution, in meters
y_resolution = 0.16 # 'rough' pixel spatial resolution, in meters
rotation = 0 # 4; # user defined rotation angle of photo in addition to the rotation based on the flight line
###############################################################

def half(val):
    return val / 2

x_half_dist = half(crop_width) * x_resolution
y_half_dist = half(crop_height) * y_resolution
# x_half_dist = 0
# y_half_dist = 0
# print("x_half_dist is: " + str(x_half_dist) + " and y_half_dist is: " + str(y_half_dist))

diagonal_length = sqrt(x_half_dist**2 + y_half_dist**2) # diagonal distance to upper right-hand corner of photo
a_angle = atan(x_half_dist / y_half_dist) # angle to upper right-hand corner of photo, measured from 0 degrees (ie., "north")
b_angle = radians(180) - a_angle # angle to lower right-hand corner of photo, measured from 0 degrees (ie., "north")
# diagonal_length = 0 # diagonal distance to upper right-hand corner of photo
# a_angle = 0 # angle to upper right-hand corner of photo, measured from 0 degrees (ie., "north")
# b_angle = 0 # angle to


def img_georef(argv):
    if len(argv) <2:
        print('You must supply the name of a .csv file with 3 fields: photograph filename, x coordinate of photo center , y coordinate of photo center')
        return -1

    if not os.path.exists(path_to_images + 'output2019.03.18'):
        os.makedirs(path_to_images + 'output2019.03.18')

    first_photo = True
    with open(argv[1], "r") as photo_list:
        photo_num = 1
        # get the count of the number of photographs
        photos = csv.reader(photo_list, delimiter=",")
        photo_count = sum(1 for _ in photos)
        photo_list.seek(0)

        photos = csv.reader(photo_list, delimiter=",")
        for photo in tqdm(photos):
            p = photo[0]
            Cx = float(photo[1])
            Cy = float(photo[2])
            x_half_dist = half(crop_width) * float(photo[8])
            y_half_dist = half(crop_height) * float(photo[8])
            diagonal_length = sqrt(x_half_dist**2 + y_half_dist**2) # diagonal distance to upper right-hand corner of photo
            a_angle = atan(x_half_dist / y_half_dist) # angle to upper right-hand corner of photo, measured from 0 degrees (ie., "north")
            b_angle = radians(180) - a_angle # angle to lower right-hand corner of photo, measured from 0 degrees (ie., "north")
            
            if first_photo:
                Px = float(linecache.getline(argv[1], 2).split(',')[1])
                Py = float(linecache.getline(argv[1], 2).split(',')[2].strip('\n'))
                first_photo = False
                clip_georeference(p, Cx, Cy, Px, Py) # need to fix this so the first photo is rotated correctly
            else:
            	clip_georeference(p, Cx, Cy, Px, Py)

            Px = Cx
            Py = Cy
            
#            print(("Completed " + str(photo_num) + " of " + str(photo_count)), end="\r")
            photo_num += 1
        print()

def clip_georeference(photo, center_x, center_y, prev_x, prev_y):
    delta_x = center_x - prev_x
    delta_y = center_y - prev_y

    if (delta_y == 0):
        if (delta_x > 0):
            basic_rotation = radians(90)
        else:
            basic_rotation = radians(270)
    else:
        basic_rotation = atan(delta_x/delta_y)

    if (delta_x >= 0 and delta_y > 0):                          # first quadrant
        flight_rotation = basic_rotation
    elif (delta_x > 0 and delta_y <= 0):                        # second quadrant
        flight_rotation = radians(180) + basic_rotation
    elif (delta_x <= 0 and delta_y < 0):                        # third quadrant
        flight_rotation = radians(180) + basic_rotation
    elif (delta_x < 0 and delta_y >= 0):                        # fourth quadrant
        flight_rotation = radians(360) + basic_rotation
    else:
        print("Error determining flight path quadrant")
        sys.exit()

    total_rotation = flight_rotation + radians(rotation)

    with Image(filename=path_to_images + photo) as img:
        with img.clone() as i:
            i.crop(width=crop_width, height=crop_height, gravity='center')
            i.rotate(degrees(total_rotation))
            i.format = 'tif'
            output_name = path_to_images + 'output2019.03.18/new_' + os.path.splitext(photo)[0] + '.tif'
            i.save(filename=output_name)

            Ax = sin(a_angle + total_rotation) * diagonal_length # X coordinate of upper right hand coordinate after rotation
            Ay = cos(a_angle + total_rotation) * diagonal_length # Y coordinate of upper right hand coordinate after rotation
            Bx = sin(b_angle + total_rotation) * diagonal_length # X coordinate of lower right hand coordinate after rotation
            By = cos(b_angle + total_rotation) * diagonal_length # Y coordinate of lower right hand coordinate after rotation

            rotated_x_shift = cos(total_rotation) * y_shift + sin(total_rotation) * x_shift
            rotated_y_shift = cos(total_rotation) * x_shift - sin(total_rotation) * y_shift

            ulx = center_x + min(Ax, Bx, -Ax, -Bx) + rotated_x_shift
            uly = center_y + max(Ay, By, -Ay, -By) + rotated_y_shift
            lrx = center_x + max(Ax, Bx, -Ax, -Bx) + rotated_x_shift
            lry = center_y + min(Ay, By, -Ay, -By) + rotated_y_shift

            ds = gdal.Open(output_name, gdal.GA_Update)

            sr = osr.SpatialReference()
            if sr.SetFromUserInput(ogc_wkt) != 0:
                print('Failed to process SRS definition: %s' % ogc_wkt)
                return -1

            wkt = sr.ExportToWkt()
            ds.SetProjection(wkt)

            gt = [ ulx, (lrx - ulx) / ds.RasterXSize, 0, uly, 0, (lry - uly) / ds.RasterYSize ]
            ds.SetGeoTransform(gt)

def main():
    return img_georef(sys.argv)

if __name__ == '__main__':
    img_georef(sys.argv)
