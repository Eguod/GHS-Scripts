from dataclasses import dataclass
import os
import re
import shutil
import zipfile
from natsort import ns, natsorted
from tqdm import tqdm

# TODO [2020] 異世界ねぇちゃんは、イク時しか魔法を使えない [官方中文] (1-3话全)
# -> (1-3话全) [ゐちぼっち (一宮夕羽)] 異世界ねぇちゃんは、イク時しか魔法を使えない
#  (1-3话全) is useless, should be removed.
# Should be [ゐちぼっち (一宮夕羽)] 異世界ねぇちゃんは、イク時しか魔法を使えない 1-3

# TODO [2023.06] 巨乳水着グラビアアイドル (30代) の末期 -> (30代) [いちごクレープ大盛組 (横十輔)] 巨乳水着グラビアアイドル

# Set of the common suffixes of image files:
image_suf_set = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.psd', '.raw', '.heif', '.indd', '.svg'}

'''
The file structure should be like:

root
|-  3925-[ぶるーびーん (要青豆)]
    |- 1.同人志
        |- (C77) そらなまこ (うみものがたり)
        |- [PIXIV] うちのコンゴウさん 1-45 (蒼き鋼のアルペジオ、艦隊これくしょん -艦これ-)
    |- 2.商业志
        |- [09.08] 若い人はいいっ☆ (COMICメガストアH 2009年8月号) [seraphicmoon汉化]
        |- 注：[色情乱れ妻嬲り 後編] 确实是坑了.txt
    |- 3.单行本
        |- [2008] 色香のヒミツ [gnapiat掃圖]
    |- 4.画集
        |- PIXIV 全投稿作品集 (自整理 592P 截止2023.04.13 按发布时间先后排序)

'''

def split_comic_name(s):
    res_list = []
    if len(s) == 0:
        return res_list
    
    i=0
    while i<len(s):
        if s[i] == '[':
            res_list.append({
                "type": '[]',
                "content": ""
            })
            start = i
            while i<len(s) and not s[i]==']':
                i+=1
            res_list[-1]["content"] = s[start+1:i].strip()
            i+=1
        elif s[i] == '(':
            res_list.append({
                "type": '()',
                "content": ""
            })
            start = i
            while i<len(s) and not s[i]==')':
                i+=1
            res_list[-1]["content"] = s[start+1:i].strip()
            i+=1

        elif s[i] == ' ':
            i+=1
            pass
        else:
            res_list.append({
                "type": 'c',
                "content": ""
            })
            start = i
            while i<len(s) and not s[i]=='(' and not s[i]=='[':
                i+=1
            res_list[-1]["content"] = s[start:i].strip()
        
    return res_list


def parse_comic_name(filename):
    # author = re.search(r'\[.+?\]', filename)
    # if author:
    #     author = author.group()
    #     filename = filename.replace(author, '').strip()
    # else:
    #     author = ''

    event = re.search(r'\(.*?\d.*?\)', filename)
    if event:
        event = event.group()
        filename = filename.replace(event, '').strip()
    else:
        event = ''

    series = re.search(r'\(.*?\)', filename)
    if series:
        series = series.group()
        filename = filename.replace(series, '').strip()
    else:
        series = ''

    translation_group = re.search(r'\[.+?\]', filename)
    if translation_group:
        translation_group = translation_group.group()
        filename = filename.replace(translation_group, '').strip()
    else:
        translation_group = ''

    suffix = re.search(r'\.\w+$', filename)
    if suffix:
        suffix = suffix.group()
        filename = filename.replace(suffix, '').strip()
    else:
        suffix = ''
    
    return 

@dataclass
class ComicFolder:
    filename: str
    comicname: str
    language: str
    translator: str
    time: str
    event: str
    series: str
    note: str
    pages: int
    new_name: str

@dataclass
class SecondLevelFolder:
    foldername: str
    content_list: list[ComicFolder]

@dataclass
class TopLevelFolder:
    idx: str
    filename_full: str
    author_full: str
    club_name: str
    author_name_list: str
    is_club: bool
    sub_folder_list: list[SecondLevelFolder]

# TODO: "进行中" means the comic translation is not finished yet. Then we should prefer the japanese version. 
# Only one sample is found till now, so ignore it for now.

# The selection rule is:
# 1. If the comic has chinese version, then select the chinese version
# 2. If the comic has multiple chinese versions, then select the one with 無修正 in the name.
# 3. If the comic has multiple chinese versions with 無修正 in the name, select the one with the most pages.
# 4. If all chinese versions have the same number of pages, then select the first one.
# 4. If the comic has no chinese version, then select the japanese version.
def comic_compare(comic1: ComicFolder, comic2: ComicFolder):
    if comic1.language == "CN" and comic2.language == "JP":
        return 1
    elif comic1.language == "JP" and comic2.language == "CN":
        return -1
    elif comic1.language == "CN" and comic2.language == "CN":
        if "無修正" in comic1.comicname and "無修正" not in comic2.comicname:
            return 1
        elif "無修正" not in comic1.comicname and "無修正" in comic2.comicname:
            return -1
        elif "無修正" in comic1.comicname and "無修正" in comic2.comicname:
            if comic1.pages > comic2.pages:
                return 1
            elif comic1.pages < comic2.pages:
                return -1
            else:
                return 0
        else:
            if comic1.pages > comic2.pages:
                return 1
            elif comic1.pages < comic2.pages:
                return -1
            else:
                return 0
    elif comic1.language == "JP" and comic2.language == "JP":
        if comic1.pages > comic2.pages:
            return 1
        elif comic1.pages < comic2.pages:
            return -1
        else:
            return 0
    else:
        return 0


# This function will check the top level folder list. If a comic has multiple versions,
# then it will select the best version, and remove the other versions.
# The defination of same comic is that they have the same comicname.
def clean_top_level_folder_list(top_level_folder_list: list[TopLevelFolder]):
    for top_level_folder in top_level_folder_list:
        for second_level_folder in top_level_folder.sub_folder_list:
            checked_comic_dict = {}
            for comic in second_level_folder.content_list:
                if comic.comicname in checked_comic_dict.keys():
                    if comic_compare(comic, checked_comic_dict[comic.comicname]) > 0:
                        checked_comic_dict[comic.comicname] = comic
                else:
                    checked_comic_dict[comic.comicname] = comic
            second_level_folder.content_list = list(checked_comic_dict.values())

def get_comic_number(top_level_folder_list: list[TopLevelFolder]):
    comic_number = 0
    for top_level_folder in top_level_folder_list:
        for second_level_folder in top_level_folder.sub_folder_list:
            comic_number += len(second_level_folder.content_list)
    return comic_number

def get_pages_number(top_level_folder_list: list[TopLevelFolder]):
    page_number = 0
    for top_level_folder in top_level_folder_list:
        for second_level_folder in top_level_folder.sub_folder_list:
            for comic in second_level_folder.content_list:
                page_number += comic.pages
    return page_number


def save_top_level_folder_list(top_level_folder_list: list[TopLevelFolder], root_path:str, save_path: str):
    total_pages_number = get_pages_number(top_level_folder_list)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    # process with progress bar
    with tqdm(total=total_pages_number) as pbar:
        for top_level_folder in top_level_folder_list:
            new_top_level_folder_path = os.path.join(save_path, top_level_folder.author_full)
            if not os.path.exists(new_top_level_folder_path):
                os.mkdir(new_top_level_folder_path)
            for second_level_folder in top_level_folder.sub_folder_list:
                for comic in second_level_folder.content_list:
                    new_comic_path = os.path.join(new_top_level_folder_path, comic.new_name+".zip")
                    old_comic_path = os.path.join(root_path, top_level_folder.filename_full, second_level_folder.foldername, comic.filename)
                    # Archive the whole old_comic_path (including subdir) to new_comic_path as zip (no compression). Skip the files that already exist.
                    if not os.path.exists(new_comic_path):
                        with zipfile.ZipFile(new_comic_path, "a", zipfile.ZIP_STORED) as zipf:
                            for root, dirs, files in os.walk(old_comic_path):
                                for file in files:
                                    zipf.write(os.path.join(root, file), arcname=os.path.join(comic.new_name, os.path.relpath(root, old_comic_path), file))
                                    pbar.update(1)
                    else:
                        pbar.update(comic.pages)
    print("Done! All files are saved to {}".format(save_path))
    input("Press Enter to exit...")

def get_new_comic_name(comic: ComicFolder, author_full: str):
    new_comic_name = ""
    if not comic.event=="":
        new_comic_name+="("+comic.event+")"
    new_comic_name += " [{}]".format(author_full)
    if not comic.comicname=="":
        new_comic_name+=" "+ comic.comicname
    if not comic.series=="":
        new_comic_name+=" ("+comic.series+")"
    if not comic.translator=="":
        new_comic_name+=" ["+comic.translator+"]"
    for note in comic.note:
        new_comic_name+=" ["+note+"]"
    
    return new_comic_name.strip()

def get_top_level_folder_list(files_list: list) -> tuple[list[TopLevelFolder], list[str]]:
    pattern = r"^[C\d]{1}\d{3}-\[(.+)\]"
    skip_list = []
    res_list = []
    if len(files_list)==0:
        return files_list
    for item in files_list:
        if not re.match(pattern, item):
            skip_list.append(item)
            continue
        else:
            filename_full = item
            idx = item[:4]
            author_full = item[5:]

            # Special case: [治屋武しでん] part1
            author_full = author_full.split(" part")[0]

            # The author_full could be: [author], [club (author)], [club (author1、author2、...)]

            # Special case: [サシミノワイフ (しでん)]／[治屋武しでん], only keep the first one
            if "／" in author_full:
                author_full = author_full.split("／")[0]

            author_full = author_full[1:-1]
            # [author]
            if "(" not in author_full:
                club_name = ""
                author_name_list = []
                is_club = False
            # [club (author)]
            elif "、" not in author_full:
                club_name = author_full.split('(')[0]
                author_name_list = [author_full.split('(')[-1][:-1]]
                is_club = True
            # [club (author1, author2, ...)]
            else:
                club_name = author_full.split('(')[0]
                author_name_list = author_full.split('(')[-1][:-1].split("、")
                is_club = True
            res_list.append(TopLevelFolder(idx=idx, author_full=author_full, club_name=club_name, author_name_list=author_name_list, is_club=is_club, filename_full=filename_full, sub_folder_list=[]))
    return res_list, skip_list

def pop_first_brackets(comic_name_splited):
    if len(comic_name_splited)==0:
        return ""
    i = 0
    while i<len(comic_name_splited):
        if comic_name_splited[i]["type"] == "[]":
            res = comic_name_splited.pop(i)["content"]
            return res
        i+=1
    return ""

def pop_first_parentheses(comic_name_splited):
    if len(comic_name_splited)==0:
        return ""
    i = 0
    while i<len(comic_name_splited):
        if comic_name_splited[i]["type"] == "()":
            res = comic_name_splited.pop(i)["content"]
            return res
        i+=1
    return ""

def pop_last_parentheses(comic_name_splited):
    if len(comic_name_splited)==0:
        return ""
    i = len(comic_name_splited)-1
    while i>=0:
        if comic_name_splited[i]["type"] == "()":
            res = comic_name_splited.pop(i)["content"]
            return res
        i-=1
    return ""

def get_first_c(comic_name_splited):
    if len(comic_name_splited)==0:
        return ""
    i = 0
    while i<len(comic_name_splited):
        if comic_name_splited[i]["type"] == "c":
            res = comic_name_splited[i]["content"]
            return res
        i+=1
    return ""

def is_date(string):
    if re.match(r'^[0-9.]+$', string):
        return True
    else:
        return False

def is_event(string):
    for s in string:
        if s<='9' and s>='0':
            return True
    return False

def fill_in_top_level_folder_list(top_level_folder_list):
    skip_comic_list = []
    for top_level_folder in top_level_folder_list:

        all_second_files_list = natsorted(os.listdir(os.path.join(root_path, top_level_folder.filename_full)))

        for second_file in all_second_files_list:

            second_file_path = os.path.join(root_path, top_level_folder.filename_full, second_file)

            if "动画" in second_file or "音声" in second_file:
                continue

            # TODO Some time in "画集", the title is still like other comic. Like [2018.02] モグダン イラストワークス + クリアファイル裏 [無修正]
            elif "画集" in second_file:
                # Collect the single pictures in the folder
                item_list = natsorted(os.listdir(second_file_path))
                single_images_list = []
                res_comic_list = []
                for item in item_list:
                    # If item is not a folder
                    if not os.path.isdir(os.path.join(second_file_path, item)) and item.lower().split('.')[-1] in image_suf_set:
                        single_images_list.append(comic)
                    elif os.path.isdir(os.path.join(second_file_path, item)):
                        # PIXIV FANBOX 作品集 (kemono 截止2023.07.09 标注发布时间&作品名称依次排序)
                        # PIXIV 全公开投稿 作品集 (自整理 348P 截止2023.08.06 按发布时间先后排序)
                        # ex-hentai 杂图汇总
                        # FANTIA 作品集 (kemono 截止2023.03.24 标注发布时间&作品名称依次排序)
                        comic_folder_path = os.path.join(second_file_path, item)
                        if not os.path.isdir(comic_folder_path):
                            continue

                        if item[0] == "#":
                            skip_comic_list.append(comic_folder_path)
                            continue
                        
                        event = ""
                        item_name_splited = split_comic_name(item)
                        for item_name in item_name_splited:
                            if item_name["type"] == "()" and "截止" in item_name["content"]:
                                event = item_name["content"].split("截止")[-1].split(" ")[0].strip()
                            elif item_name["type"] == "c":
                                comicname = top_level_folder.author_name_list[0] + ' ' + item_name["content"] if top_level_folder.is_club else top_level_folder.author_full + ' ' + item_name["content"]

                        comic = ComicFolder(
                            filename=item,
                            comicname=comicname,
                            language="",
                            translator="",
                            time="",
                            event=event,
                            series="",
                            note=[],
                            pages = 0,
                            new_name=""
                        )
                        comic.new_name = get_new_comic_name(comic, top_level_folder.author_full)

                        comic.pages = len((os.listdir(comic_folder_path)))
                        res_comic_list.append(comic)
                        
                if single_images_list:
                    # Create a new folder for the single images
                    single_images_folder_path = os.path.join(second_file_path, "其他杂图")
                    if not os.path.exists(single_images_folder_path):
                        os.mkdir(single_images_folder_path)
                    for single_image in single_images_list:
                        shutil.move(os.path.join(second_file_path, single_image), single_images_folder_path)
                    comic = ComicFolder(
                        filename="其他杂图",
                        comicname= top_level_folder.author_name_list[0] + ' ' + "其他杂图" if top_level_folder.is_club else top_level_folder.author_full + ' ' + "其他杂图",
                        language="",
                        translator="",
                        time="",
                        event="",
                        series="",
                        note=[],
                        pages = len(single_images_list),
                        new_name=""
                    )
                    comic.new_name = get_new_comic_name(comic, top_level_folder.author_full)
                    comic.pages = len((os.listdir(single_images_folder_path)))
                    res_comic_list.append(comic)

                top_level_folder.sub_folder_list.append(SecondLevelFolder(foldername=second_file, content_list=res_comic_list))

            elif os.path.isdir(second_file_path):

                comic_list=natsorted(os.listdir(second_file_path))

                res_comic_list = []

                for comic_folder in comic_list:

                    comic_folder_path = os.path.join(second_file_path, comic_folder)

                    if not os.path.isdir(comic_folder_path):
                        continue

                    if comic_folder[0] == "#":
                        skip_comic_list.append(comic_folder_path)
                        continue

                    # "PIXIV 全公开投稿" or "PIXIV FANBOX 作品集"
                    if "作品集" in comic_folder:
                        skip_comic_list.append(comic_folder_path)
                        continue

                    if "別スキャン" in comic_folder:
                        skip_comic_list.append(comic_folder_path)
                        continue

                    comic = ComicFolder(
                        filename=comic_folder,
                        comicname="",
                        language="",
                        translator="",
                        time="",
                        event="",
                        series="",
                        note=[],
                        pages = 0,
                        new_name=""
                    )

                    # [Time]Title(Series)(Event)[Translator][Note1][Note2]
                    # [PIXIV]Title(Series)(Event)[Translator][Note1][Note2]
                    # (Event)Title(Series)[Translator][Note1][Note2]
                    # (Event)Title(Series)
                    comic_name_splited = split_comic_name(comic_folder)
                    
                    if len(comic_name_splited) > 3 and comic_name_splited[-1]["type"]=="[]" and comic_name_splited[-2]["type"]=="[]" and comic_name_splited[-3]["type"]=="[]":
                        comic.translator = comic_name_splited[-3]["content"]
                        comic.note.append(comic_name_splited[-2]["content"])
                        comic.note.append(comic_name_splited[-1]["content"])
                    elif len(comic_name_splited) > 2 and comic_name_splited[-1]["type"]=="[]" and comic_name_splited[-2]["type"]=="[]":
                        comic.translator = comic_name_splited[-2]["content"]
                        comic.note.append(comic_name_splited[-1]["content"])
                    elif len(comic_name_splited) > 1 and comic_name_splited[-1]["type"]=="[]":
                        if "修正" in comic_name_splited[-1]["content"] or "カラー化" in comic_name_splited[-1]["content"]:
                            comic.note.append(comic_name_splited[-1]["content"])
                        else:
                            comic.translator = comic_name_splited[-1]["content"]
                    else:
                        pass

                    if comic_name_splited[0]["type"] == "[]":
                        if is_date(comic_name_splited[0]["content"]):
                            comic.time = pop_first_brackets(comic_name_splited)
                        else:
                            comic.note.append(pop_first_brackets(comic_name_splited))
                        comic.event = pop_last_parentheses(comic_name_splited)
                        comic.series = pop_last_parentheses(comic_name_splited)
                        if comic.series == "":
                            if not is_event(comic.event):
                                comic.series = comic.event
                                comic.event = ""
                    elif comic_name_splited[0]["type"] == "()":
                        comic.event = pop_first_parentheses(comic_name_splited)
                        comic.series = pop_first_parentheses(comic_name_splited)
                    elif comic_name_splited[0]["type"] == "c":
                        pass
                    else:
                        pass
                    
                    if "日原版" in comic_folder or comic.translator=="":
                        comic.language = "JP"
                    elif "英訳" in comic_folder:
                        comic.language = "EN"
                    else:
                        comic.language = "CN"
                    
                    comic.comicname = get_first_c(comic_name_splited)

                    comic.pages = len((os.listdir(comic_folder_path)))

                    comic.new_name = get_new_comic_name(comic, top_level_folder.author_full)

                    res_comic_list.append(comic)

                top_level_folder.sub_folder_list.append(SecondLevelFolder(foldername=second_file, content_list=res_comic_list))
            else:
                continue
    return skip_comic_list

if __name__ == "__main__":

    root_path = input("Please input the root path: ")
    save_path = input("Please input the save path: ")

    all_top_files_list = natsorted(os.listdir(root_path))

    top_level_folder_list, skip_list = get_top_level_folder_list(all_top_files_list)

    skip_comic_list = fill_in_top_level_folder_list(top_level_folder_list)
  
    clean_top_level_folder_list(top_level_folder_list)

    save_top_level_folder_list(top_level_folder_list, root_path, save_path)