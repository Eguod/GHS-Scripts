# -*- coding: utf-8 -*-

import os
import re

'''
Get the share link and the password from the txt file.
The share link meets the following format:
1. Start with "https://pan.baidu.com/s/"
2. All the characters after "https://pan.baidu.com/s/" are digits, letters or "_".
The password meets the following format:
1. The password is 4 digits or letters.
2. The password sometimes is attached to the share link, separated by "?pwd=".
3. If the password is not attached to the share link, then it will be indicated with "提取码：xxxx". 
   It can be in the same line with the share link or in a new line.

Here are some examples:
Example 1:
链接：https://pan.baidu.com/s/1QuAshvMs1qec6ZAvDNXzDw?pwd=4xff 
提取码：4xff 

Example 2:
https://pan.baidu.com/s/1QuAshvMs1qec6ZAvDNXzDw?pwd=4xff
'''
def extract_links_and_passwords(file_path):
    try:
        with open(file_path, 'r', encoding='gbk') as file:
            content = file.read()
    except UnicodeDecodeError as e:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError as e:
            print("Failed to decode the file: ", e)
            return [], []

    # Extract share links
    links = re.findall(r'https://pan\.baidu\.com/s/[A-Za-z0-9_-]+', content)
    if not links:
        raise ValueError("Share links not found in file.")

    # Extract passwords
    passwords = re.findall(r'(?<=\?pwd=)[A-Za-z0-9]{4}|(?<=提取码：)[A-Za-z0-9]{4}', content)
    if not passwords:
        raise ValueError("Passwords not found in file.")
    if passwords[0] == passwords[1]:
        passwords = passwords[0::2]

    return links, passwords

def get_all_txt_file(root_path):
    txt_file_list = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith('.txt'):
                txt_file_list.append(os.path.join(root, file))
    return txt_file_list

if __name__ == '__main__':
    share_link_list = []
    password_list = []
    input_file = input("输入文件/文件夹路径：")
    output_file = input("输出文件路径：")
    if os.path.isdir(input_file):
        txt_file_list = get_all_txt_file(input_file)
        for file in txt_file_list:
            share_links, passwords = extract_links_and_passwords(file)
            share_link_list += share_links
            password_list += passwords
    else:
        share_link, password = extract_links_and_passwords(input_file)
        share_link_list.append(share_link)
        password_list.append(password)
    
    # Write the share link and password to the txt file
    with open(os.path.join(output_file, 'share_link.txt'), 'w') as file:
        for share_link, password in zip(share_link_list, password_list):
            file.write(share_link + '?pwd=' + password + '\n')