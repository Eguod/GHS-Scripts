import glob
import os
from tkinter import image_names
import fitz
from natsort import ns, natsorted
import cv2
import numpy as np

def cv2imread(img_path):
    return cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), -1)

# 中文问题
def cv2imwrite(filename,img):
    cv2.imencode('.jpg', img)[1].tofile(filename)

class PdfImgConvertor:
    def __init__(self, input_path, mode = 'single') -> None:
        self.legal_extension_list = ['.bmp', '.dib', '.png', '.jpg', '.jpeg', '.pbm', '.pgm', '.ppm', '.tif', '.tiff']
        self.mode = mode # 'single', 'seperated'
        self.input_path = input_path
        self.log_path = os.path.join(self.input_path, 'log.txt')

    def is_image(self, name):
        if not type(name)==str:
            return False
        return name.lower().endswith(('.bmp', '.dib', '.png', '.jpg', '.jpeg', '.pbm', '.pgm', '.ppm', '.tif', '.tiff'))

    def resize(self, image_path_list, output_path, info='', compress_rate=0.5) -> None:
        if not os.path.isdir(output_path):
            os.mkdir(output_path)
        for id, image_path in enumerate(image_path_list):
            print("{}/{} {} {}".format(id, len(image_path_list),info, image_path))
            img = cv2imread(image_path)
            width, heigh = img.shape[:2]
            # target height = 1000
            img_resize = cv2.resize(img, (int(heigh*compress_rate), int(width*compress_rate)),
                                    interpolation=cv2.INTER_AREA)
            cv2imwrite(os.path.join(output_path, 'resize_'+os.path.basename(image_path)), img_resize)
            with open(self.log_path, 'a',encoding='utf-8') as log:
                log.write(image_path+'\n')

    def create_pdf(self, image_path_list, output_pdf_path, compress_rate = 1, info='') -> None:
        doc = fitz.open()
        for id, image_path in enumerate(image_path_list):
            print("Adding: {}/{} {} {}".format(id, len(image_path_list),info, image_path))
            imgdoc = fitz.open(image_path)
            pdfbytes = imgdoc.convertToPDF()
            imgpdf = fitz.open("pdf", pdfbytes)
            doc.insertPDF(imgpdf)
            with open(self.log_path, 'a',encoding='utf-8') as log:
                log.write(image_path+'\n')
        if not compress_rate ==1:
            out_pdf = fitz.open()
            for id, page in enumerate(doc):
                print("Compressing: {}/{} {} {}".format(id, len(image_path_list), info, output_pdf_path))
                pix = page.get_pixmap(matrix=fitz.Matrix(compress_rate, compress_rate)) # double resolution for better image quality
                out_page = out_pdf.new_page(width=page.rect.width, height=page.rect. height)
                out_page.insert_image(page.rect, stream=pix.tobytes("png"))
            out_pdf.save(output_pdf_path, deflate=True)
            out_pdf.close()
        else:
            doc.save(output_pdf_path)
            doc.close()
    
    def get_all_images(self, folder_path):
        file_path_list = []
        if not os.path.isdir(folder_path):
            print("ERROR: {} does not exist!".format(folder_path))
            return
        else:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if self.is_image(file) == False:
                        print("WARNING: {} is not image. Skipped.".format(file))
                    else:
                        file_path_list.append(os.path.join(root, file))
        return file_path_list
    
    def get_top_dirs(self, folder_path):
        top_dir_list = []
        for item in os.listdir(folder_path):
            if os.path.isdir(os.path.join(folder_path, item)):
                top_dir_list.append(os.path.join(folder_path, item))
        return top_dir_list

    def recoverpix(self, doc, item):
        xref = item[0]  # xref of PDF image
        smask = item[1]  # xref of its /SMask
        return doc.extract_image(xref)

    def get_imgs(self, input_pdf_path_list, output_img_path):
        counter = 1
        for pdf_path in input_pdf_path_list:
            doc = fitz.open(pdf_path)
            page_count = doc.page_count  # number of pages
            xreflist,imglist = [],[]
            for pno in range(page_count):
                il = doc.get_page_images(pno)
                imglist.extend([x[0] for x in il])
                for img in il:
                    xref = img[0]
                    if xref in xreflist:
                        continue
                    width = img[2]
                    height = img[3]
                    image = self.recoverpix(doc, img)
                    n = image["colorspace"]
                    imgdata = image["image"]
                    imgfile = os.path.join(output_img_path, "{:04d}.{}".format(counter, image["ext"]))
                    counter +=1
                    fout = open(imgfile, "wb")
                    fout.write(imgdata)
                    fout.close()
                    xreflist.append(xref)
                    print("Saved image: {}".format(imgfile))

    def run(self):
        log_path = os.path.join(self.input_path, 'log.txt')

        if self.mode == 'single':
            image_path_list = natsorted(self.get_all_images(self.input_path), alg=ns.PATH)
            output_pdf_path = os.path.join(self.input_path, os.path.basename(self.input_path)+'.pdf')
            self.create_pdf(image_path_list, output_pdf_path, compress_rate=1)
        elif self.mode == 'seperated':
            dirs = self.get_top_dirs(self.input_path)
            for id, dir in enumerate(dirs):
                image_path_list = natsorted(self.get_all_images(dir),alg=ns.PATH)
                output_pdf_path = os.path.join(self.input_path, os.path.basename(dir)+'.pdf')
                self.create_pdf(image_path_list, output_pdf_path, info="{}/{}".format(id,len(dirs)))
        elif self.mode == 'resize':
            compress_rate = eval(input("compress_rate?"))
            dirs = self.get_top_dirs(self.input_path)
            for id, dir in enumerate(dirs):
                image_path_list = natsorted(self.get_all_images(dir),alg=ns.PATH)
                output_path = os.path.join(self.input_path, 'resize_'+os.path.basename(dir))
                self.resize(image_path_list, output_path, info="{}/{}".format(id,len(dirs)), compress_rate=compress_rate)
        elif self.mode == 'singlepics':
            pdf_path_list = [os.path.join(self.input_path, i) for i in natsorted(os.listdir(self.input_path),alg=ns.PATH)]
            output_dir = os.path.join(self.input_path, os.path.basename(pdf_path_list[0]).split('.')[0])
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            self.get_imgs(pdf_path_list, output_dir)
        elif self.mode == 'multipics':
            pdf_path_list = [os.path.join(self.input_path, i) for i in natsorted(os.listdir(self.input_path),alg=ns.PATH)]
            for pdf_path in pdf_path_list:
                output_dir = os.path.join(self.input_path, os.path.basename(pdf_path).split('.')[0])
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                self.get_imgs([pdf_path], output_dir)


if __name__ == '__main__':

    while 1:
        input_path = input("目录：（如：D:\韩漫\美丽新世界）")
        while 1:
            mode = input("请选择模式：（1）图片合成单个pdf\n（2）图片合成多个pdf\n (3) 压缩图片\n (4) 所有pdf提取图片\n (5) pdf分别提取图片\n 1\\2\\3\\4\\5:")
            if mode == '1':
                m = 'single'
                break
            elif mode == '2':
                m = 'seperated'
                break
            elif mode == '3':
                m = 'resize'
                break
            elif mode == '4':
                m = 'singlepics'
                break
            elif mode == '5':
                m = 'multipics'
                break
            else:
                print("Invalid Input")

        convertor = PdfImgConvertor(input_path = input_path, mode=m)
        convertor.run()