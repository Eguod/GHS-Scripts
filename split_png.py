import cv2
import os

path = input("输入文件夹路径：")
height = 3200

img_list = os.listdir(path)
output_path = os.path.join(path, 'output')
if not os.path.isdir(output_path):
    os.mkdir(output_path)

counter = 0
for img_name in sorted(os.listdir(path)):
    img = cv2.imread(os.path.join(path,img_name))
    h, w, _ = img.shape
    end = 0
    
    output_name = os.path.join(output_path, "{:04d}.png".format(counter))

    if h%height == 0:
        for i in range(int(h/3200)):
            output_name = os.path.join(output_path, "{:04d}.png".format(counter))
            cv2.imwrite(output_name,img[i*height:(i+1)*height,:,:])
            counter+=1
    elif h%height > height/2:
        for i in range(int(h/3200)):
            output_name = os.path.join(output_path, "{:04d}.png".format(counter))
            cv2.imwrite(output_name,img[i*height:(i+1)*height,:,:])
            counter+=1
        output_name = os.path.join(output_path, "{:04d}.png".format(counter))
        cv2.imwrite(output_name,img[int(h/3200)*height:,:,:])
        counter+=1
    else:
        if int(h/3200)-1<0:
            output_name = os.path.join(output_path, "{:04d}.png".format(counter))
            cv2.imwrite(output_name,img[:,:,:])
            counter+=1
        else:
            for i in range(int(h/3200)-1):
                output_name = os.path.join(output_path, "{:04d}.png".format(counter))
                cv2.imwrite(output_name,img[i*height:(i+1)*height,:,:])
                counter+=1
            output_name = os.path.join(output_path, "{:04d}.png".format(counter))
            cv2.imwrite(output_name,img[(int(h/3200)-1)*height:,:,:])
            counter+=1
    print(counter, img_name)