#!/usr/bin/env python3
import rospy
import math
from sensor_msgs.msg import LaserScan
import rospy
import numpy as np
import matplotlib
from geometry_msgs.msg import Pose
import matplotlib.pyplot as plt
import numpy as np
import time
from tools import n_closest
from tools import rotate_2d_vector
from tfTools import get_2d_point_moved_using_vector
from tfTools import get_transform_vector_from_pose
from geometry_msgs.msg import Point
from std_msgs.msg import Float64
import warnings
from std_msgs.msg import Int64MultiArray
from drone_control.msg import MyNumpy



class MappingNode():
    def __init__(self):
        self.node=rospy.init_node("mapper",anonymous=True)
        self.subDronePos=rospy.Subscriber("dronePosition",Point,self.get_drone_position)
        self.subOrientation=rospy.Subscriber("eulerInfo",Float64,self.get_drone_orientation)
        self.subLaser=rospy.Subscriber("coppeliaLaserInfo",LaserScan,self.get_laser_data)
        self.pubMyMap=rospy.Publisher("myMap",MyNumpy,queue_size=1)
        self.x_min=-5
        self.x_max=5
        self.y_min=-5
        self.y_max=5
        self.map_resolution=0.05
        dimension_x=int((self.x_max-self.x_min)/self.map_resolution)
        dimension_y=int((self.y_max-self.y_min)/self.map_resolution)
        self.map_memmory=np.zeros((dimension_y,dimension_x),np.int32)#first for x secound for y
        self.max_points=1024
        self.my_plot=None
        self.plot_fig=None
        self.is_laser_data=False
        self.is_drone_pos_data=False
        self.is_euler_data=False
        self.is_first_datas=True
        self.drone_pos=None
        self.theta=None
        self.last_print_time=time.time()
        self.buffor_range=4
        #fig = plt.figure()
        #self.ax = fig.add_subplot(1,1,1)
        rospy.loginfo("nowe dane test")
        warnings.filterwarnings("ignore")
        self.time_euler=time.time()
        self.time_pos=time.time()
        rospy.spin()
        






    def get_drone_position(self,msg):
        
        self.drone_pos=[msg.x,msg.y,msg.z]
        self.is_drone_pos_data=True



    def get_drone_orientation(self,msg):
       
        self.theta=msg.data
        self.is_euler_data=True

      

    def transfer_points(self,x_array,y_array,angle):
        for i,x_p in enumerate(x_array):
            x=x_array[i]
            y=y_array[i]
            
            #rospy.loginfo("angle %f"%(angle))
            
           # x,y=rotate_2d_vector([x,y],np.pi)
            x,y=rotate_2d_vector([x,y],angle)
            x,y=get_2d_point_moved_using_vector(self.drone_pos,(x,y))
            x_array[i]=x
            y_array[i]=y
        return (x_array,y_array)



    def get_point_on_map_index(self,x,y):

        x_i = int(round((x - self.x_min) / self.map_resolution))
        y_i= int(round((y - self.y_min) / self.map_resolution))
        return (x_i,y_i)

    def get_drone_x_y_arrays(self,x_array):
        x=np.zeros(np.size(x_array))
        y=np.zeros(np.size(x_array))
        y[:]=self.drone_pos[1]
        x[:]=self.drone_pos[0]
        return x,y
    
        
    def get_laser_data(self,msg):
        
        
        
        self.counter=0
        self.is_laser_data=True
        
        
        laser_data=msg.ranges
        #rospy.loginfo("liczby: %d"%(len(laser_data)))
        conuter=0
        #points_list=self.get_points(old_data)
        if(self.theta==None or self.drone_pos==None):
            return

        x_array,y_array=self.get_x_y(laser_data)
        x_array,y_array=self.transfer_points(x_array,y_array,self.theta)


        self.update_map_memory(x_array,y_array,self.map_resolution,self.x_min,self.y_min)
        if(time.time()-self.last_print_time>0.01):
            #self.show_rays(x_array,y_array)
        
            self.show_map()
            self.last_print_time=time.time()
            myMapMsg=MyNumpy()
            myMapMsg.data=self.map_memmory.flatten().tolist()
            self.pubMyMap.publish(myMapMsg)
        #rospy.loginfo("nowe dane test %f"%(self.last_data_publication_time))
        
        #self.test()
        #rospy.loginfo("nowe dane %f"%(time.time()-self.last_data_publication_time))


    def update_map_memory(self,x_array,y_array,map_resolution,x_min,y_min):
        for i, x in enumerate(x_array):
            x_i,y_i=self.get_point_on_map_index(x_array[i],y_array[i])
            self.map_memmory[y_i][x_i]=1
            neighbours=n_closest(self.map_memmory,(y_i,x_i),self.buffor_range)
            neighbours[neighbours!=1]=2

    def get_points_from_memory(self,value):
        points_indexs=np.where(self.map_memmory==value)
        x_index_array=points_indexs[1]
        y_index_array=points_indexs[0]
        x_array=x_index_array*self.map_resolution
        x_array=x_array+self.x_min

        y_array=y_index_array*self.map_resolution
        y_array=y_array+self.y_min


        return (x_array,y_array)
    


    def convert_index_to_point(self,x_i,y_i):
        x=x_i*self.map_resolution
        x=x+self.x_min

        y=y_i*self.map_resolution
        y=y+self.y_min
        return (x,y)

    def show_map(self):
        #plt.figure(figsize=(6,10))

        x_obstacle_array,y_obstacle_arrray=self.get_points_from_memory(1)
        x_buffor,y_buffor=self.get_points_from_memory(2)

        if(self.is_first_datas):
            plt.show()
            plt.ion()
            
            self.is_first_datas=False

        plt.plot(x_obstacle_array,y_obstacle_arrray, "s",markersize=1) # lines from 0,0 to the 
        plt.plot(x_buffor,y_buffor, "s",markersize=1) #buffor
        plt.plot((self.drone_pos[0]),(self.drone_pos[1]),"o",markersize=5)#drone

        plt.ylim((-5,5))
        plt.xlim((-5,5))
  
        plt.draw()
        plt.pause(0.00000001)
        plt.clf()
        
 

    def show_rays(self,x_array,y_array):
        #plt.figure(figsize=(6,10))
        x_drone_array,y_drone_array=self.get_drone_x_y_arrays(x_array)
        
        if(self.is_first_datas):
            plt.show()
            plt.ion()
            
            self.is_first_datas=False

        plt.plot([x_array, x_drone_array],[y_array, y_drone_array], "ro-") # lines from 0,0 to the 

        plt.ylim((-5,5))
        plt.xlim((-5,5))
        #plt.axis("equal")
        #bottom, top = plt.ylim()  # return the current ylim
        #plt.ylim((top, bottom)) # rescale y axis, to match the grid orientation
       # plt.grid(True)
        plt.draw()
        plt.pause(0.00000001)
        plt.clf()
        
     



    def get_points(self,laser_data):
        points_list=[]
        current_point=[]
        for i,cordinate in enumerate(laser_data):
            
            if (i+1)%3==0:
                # current_point.append(cordinate)
                points_list.append(current_point)
                current_point=[]
            else:
                current_point.append(cordinate)
        return points_list


    def get_x_y(self,old_data):
        x=[]
        y=[]
        current_point=[]
        for i,cordinate in enumerate(old_data):
            
            if (i+1)%3==0:
                x.append(current_point[0])
                y.append(current_point[1])
                current_point=[]
            else:
                
                current_point.append(cordinate)

        x=np.array(x)
        y=np.array(y)
        return (x,y)

if __name__ == "__main__":

    newNode=MappingNode()    

# def create_map(laser_data,laser_step,laser_min):
#     """
#     Reading LIDAR laser beams (angles and corresponding distance data)
#     """
#     measures = [line.split(",") for line in open(f)]
#     angles = []
#     distances = []
#     for measure in measures:
#         angles.append(float(measure[0]))
#         distances.append(float(measure[1]))
#     angles = np.array(angles)
#     distances = np.array(distances)
#     return angles, distances

# def plot_test():


#     # Data for plotting
#     t = np.arange(0.0, 2.0, 0.01)
#     s = 1 + np.sin(2 * np.pi * t)

#     fig, ax = plt.subplots()
#     ax.plot(t, s)

#     ax.set(xlabel='time (s)', ylabel='voltage (mV)',
#         title='About as simple as it gets, folks')
#     ax.grid()

#     fig.savefig("test.png")
#     plt.show()