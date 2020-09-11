# Upload 176
from datetime import datetime
from distutils import dir_util, file_util
import filecmp
import itertools
import logging
import os
import pathlib
import random
import shutil
import sys

from matplotlib import pyplot as plt
import networkx as nx
import pytz


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(levelname)s; %(asctime)s; %(name)s; %(message)s')
file_handler = logging.FileHandler('follow_wit.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

streamer = logging.StreamHandler()
streamer.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(streamer)


def make_dir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        logger.error(f"{path} already exist")

    except OSError:
        logger.error(f"Creation of the directory {path} failed ")
    else:
        logger.info(f"Successfully created the directory {path}")


def init():
    base_dirct = ("images", "staging_area")
    current = os.getcwd()
    path = os.path.join(current, ".wit")
    make_dir(path)
    for diro in base_dirct:
        make_dir(os.path.join(path, diro))
    with open(os.path.join(os.getcwd(), "activated.txt"), "w") as act:
        act.write("master")


def search_wit(search=None, subfolder=None):
    if not search:
        search = os.getcwd()
    search_in = pathlib.Path(search)
    x = 0
    while x == 0:
        for madrob in os.listdir(search_in):
            if madrob == ".wit":
                x += 1
                if not subfolder:
                    return pathlib.Path(search_in)
                return os.path.join(search_in, os.path.join(madrob, subfolder))
        search_in = search_in.parent
        if len(search_in.parts) == 1:
            x += 1
            logger.info(
                f"no .wit folder found in {search} or its parent dirs")
            return False


def create_hierarchy(begining):
    order = []
    if os.path.isfile(begining):
        directory = pathlib.Path(begining).parent
    else:
        directory = pathlib.Path(begining)
    try:
        while ".wit" not in os.listdir(directory):
            order.append(directory.name)
            if ".wit" not in os.listdir(directory):
                directory = directory.parent
        found = search_wit(directory, "staging_area")
        order.reverse()
        for directory_add in order:
            found = os.path.join(found, directory_add)
            if not os.path.exists(found):
                os.mkdir(found)
    except FileNotFoundError:
        logger.error("No file like it found in the system!")
        return None
    return found


def add(add_what):
    check = search_wit(subfolder="staging_area")
    if not check:
        logger.info(f"couldn't add the file/dir {add_what}")
        return
    where_to = create_hierarchy(add_what)
    if os.path.isdir(add_what):
        dir_util.copy_tree(add_what, where_to)
        logger.info(f"dir {add_what} has been added")
    if os.path.isfile(add_what):
        file_util.copy_file(add_what, where_to)
        logger.info(f"file {add_what} has been added")


def make_new_files(commit_id, images_folder, MESSAGE):
    commit_folder = os.path.join(images_folder, commit_id)
    while os.path.exists(commit_folder):
        commit_id = "".join(random.choices("1234567890abcdef", k=40))
        commit_folder = os.path.join(images_folder, commit_id)
    make_dir(commit_folder)
    commit_file = os.path.join(images_folder, commit_id + ".txt")
    with open(commit_file, "w") as commit_file:
        commit_file.write(f"""parent=None
date={datetime.now(pytz.timezone('Asia/Jerusalem'))}
message={MESSAGE}""")
    dir_util.copy_tree(search_wit(subfolder="staging_area"), commit_folder)
    logger.info(f"current staging_area has been added to {commit_id}")
    ref_file = os.path.join(search_wit(), "references.txt")
    with open(ref_file, "w") as reference_file:
        reference_file.write(f"""HEAD={commit_id}
master={commit_id}\n""")


def check_same_directory(walker):
    list_of = []
    for _root, direct, files in os.walk(walker):
        for name in files:
            list_of.append([direct, name])
    list_of.sort()
    return list_of


def update_files(commit_id, images_folder, MESSAGE):
    commit_folder = os.path.join(images_folder, commit_id)
    cur_ref_file = os.path.join(search_wit(), "references.txt")
    with open(cur_ref_file, "r") as reference_file:
        file = reference_file.read()
        head = file.splitlines()[0].split("=")[1]
        # master = file.splitlines()[1].split("=")[1]
        is_branch = 0
        for _line in file.splitlines():
            is_branch += 1
        staging_list = check_same_directory(
            search_wit(subfolder="staging_area"))
        cur_1_list = check_same_directory((os.path.join(images_folder, head)))
        if staging_list == cur_1_list:
            logger.info(
                f"Tried to copy the same files as the last save, {head}")
            return False
        make_dir(commit_folder)
        dir_util.copy_tree(search_wit(subfolder="staging_area"), commit_folder)
        logger.info(f"current staging_area has been added to {commit_id}")
    if is_branch > 2:
        update_branch(commit_id, get_branch())
    else:
        with open(cur_ref_file, "w") as update_reference_file:
            update_reference_file.write(f"""HEAD={commit_id}
master={commit_id}\n""")
    commit_file = os.path.join(images_folder, commit_id + ".txt")
    with open(commit_file, "w") as new_commit_file:
        new_commit_file.write(f"""parent={head}
date={datetime.now(pytz.timezone('Asia/Jerusalem'))}
message={MESSAGE}""")


def commit(MESSAGE):
    if not search_wit():
        logger.info("Tried to preform commit, No wit in this directory!")
        return
    commit_id = "".join(random.choices("1234567890abcdef", k=40))
    images_folder = search_wit(subfolder="images")
    if not os.listdir(images_folder):
        make_new_files(commit_id, images_folder, MESSAGE)
    else:
        update_files(commit_id, images_folder, MESSAGE)


def get_diff_files(dir_comp):
    diff_list = []
    for file in dir_comp.right_only:
        diff_list.append(file)
    for dirs in dir_comp.subdirs.values():
        diff_list.append(get_diff_files(dirs))
    listo = [file for file in diff_list if file]
    return listo


def get_diff_content(dir_comp):
    diff_list = []
    for direct in dir_comp.subdirs.values():
        directos = [file for file in direct.diff_files if file]
        diff_list.append(directos)
        for sub_dir in direct.subdirs.values():
            diff_list.append(get_diff_content(sub_dir))
    listo = [file for file in diff_list if file]
    return listo


def status(dont_print=None):
    if not search_wit():
        logger.info(
            "Tried to preform status, No wit folder found in this directory!")
        return
    cur_ref_file = os.path.join(search_wit(), "references.txt")
    try:
        with open(cur_ref_file, "r") as ref_file:
            ref_file = ref_file.read()
            head = ref_file.splitlines()[0].split("=")[1]
    except FileNotFoundError:
        logger.error("no reference file found!")
        return
    commit_dir = os.path.join(search_wit(subfolder="images"), head)
    stage_dir = search_wit(subfolder="staging_area")
    head_dir = search_wit()
    changes = get_diff_files(filecmp.dircmp(commit_dir, stage_dir))
    content = get_diff_content(filecmp.dircmp(stage_dir, head_dir, ignore=[
        "activated.txt", ".wit", "follow_wit.log", "references.txt"]))
    untrack = get_diff_files(filecmp.dircmp(stage_dir, head_dir, ignore=[
        "activated.txt", ".wit", "follow_wit.log", "references.txt"]))
    if not dont_print:
        print(f"""current commit: {head}
Changes to be committed:
{changes}
{"--" * 30}
Changes not staged for commit:
{content}
{"--" * 30}
Untracked files:
{untrack}
{"--" * 30}
""")
    else:
        return changes, content, untrack


def get_master_head():
    cur_ref_file = os.path.join(search_wit(), "references.txt")
    with open(cur_ref_file, "r") as reference_file:
        file = reference_file.read()
        head = file.splitlines()[0].split("=")[1]
        master = file.splitlines()[1].split("=")[1]
        if len(file.splitlines()) > 2:
            brancher = True
        else:
            brancher = False
    return head, master, brancher


def update_branch(commit_id, branch):
    cur_ref_file = os.path.join(search_wit(), "references.txt")
    with open(cur_ref_file, "r") as change_refrence:
        x = -1
        change = change_refrence.readlines()
        for line in change:
            x += 1
            if branch == line.strip("\n").split("=")[0]:
                good_line = x
                change[good_line] = (f"{branch}={commit_id}\n")
        change[0] = (f"HEAD={commit_id}\n")
        with open(cur_ref_file, "w") as change_refrence:
            change_refrence.writelines(change)


def update_ref_file(commit_id, branch=None):
    head, master, brancher = get_master_head()
    cur_ref_file = os.path.join(search_wit(), "references.txt")
    if check_all_branches(branch):
        if check_all_branches(branch) == commit_id:
            update_branch(commit_id, branch)
        return
    if brancher:
        if branch:
            with open(cur_ref_file, "a") as change_refrence:
                change_refrence.write(f"{branch}={head}\n")
        else:
            with open(cur_ref_file, "r") as change_refrence:
                change = change_refrence.readlines()
                change[0] = (f"HEAD={commit_id}\n")
                change[1] = (f"master={commit_id}\n")
            with open(cur_ref_file, "w") as change_refrence:
                change_refrence.writelines(change)
    else:
        if branch:
            with open(cur_ref_file, "a") as change_refrence:
                change_refrence.write(f"{branch}={head}\n")
        else:
            with open(cur_ref_file, "w") as change_refrence:
                change_refrence.write(f"HEAD={commit_id}\nmaster={master}\n")


def delete_files(untrack):
    ignore_files = ["follow_wit.log", "references.txt", "activated.txt"]
    dirs_to_ignore = os.path.join(".wit", "images")
    for root, dirs, files in os.walk(search_wit()):
        if dirs_to_ignore not in root:
            for tik in dirs:
                if tik not in untrack:
                    for name in files:
                        if name not in untrack:
                            if name not in ignore_files:
                                try:
                                    os.remove(os.path.join(root, name))
                                except OSError:
                                    pass
    for root, dirs, _files in os.walk(search_wit()):
        for name in dirs:
            if dirs_to_ignore not in root:
                if name not in ignore_files:
                    if name not in untrack:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except OSError:
                            pass


def check_all_branches(branch):
    with open(os.path.join(search_wit(), "references.txt"), "r") as ref_file:
        ref = ref_file.readlines()
        for line in ref:
            if line.strip("\n").split("=")[0] == branch:
                return line.strip("\n").split("=")[1]
            if line.strip("\n").split("=")[1] == branch:
                return False
        return False


def checkout(commit_id):
    if not search_wit():
        logger.info(
            "Tried to preform checkout, No wit found in this directory!")
        return
    changes, content, untrack = status(True)
    try:
        changes = list(itertools.chain.from_iterable(changes))
        content = list(itertools.chain.from_iterable(content))
        untrack = list(itertools.chain.from_iterable(untrack))
    except TypeError:
        logger.error()
    if (changes or content):
        logger.warning(
            f"cant checkout to {commit_id}, files need to commit and/or stage")
        return
    head, master, brancher = get_master_head()
    if check_all_branches(commit_id):
        with open(os.path.join(search_wit(), "activated.txt"), "w") as act:
            act.write(commit_id)
        name = commit_id
        commit_id = check_all_branches(commit_id)
    else:
        brancher = False
    commit_folder = os.path.join(search_wit(subfolder="images"), commit_id)
    head_folder = str(search_wit())
    delete_files(untrack)
    dir_util.copy_tree(commit_folder, search_wit(subfolder="staging_area"))
    dir_util.copy_tree(commit_folder, head_folder)
    logger.info(f"checkout to {commit_id} has been done!")
    if not brancher:
        update_ref_file(commit_id)
    else:
        update_ref_file(commit_id, name)


def get_father_child(head, full_path=None):
    im_your_father = []
    while head != "None":
        image_fold = os.path.join(search_wit(
            subfolder="images"), head + ".txt")
        with open((image_fold), "r") as file:
            file = file.read()
            header = file.splitlines()[0].split("=")[1]
            if header == "None":
                if im_your_father == []:
                    im_your_father.append((header, head))
                return im_your_father
            if full_path:
                im_your_father.append((head, header))
            else:
                im_your_father.append((head[:6], header[:6]))
            head = header
    return im_your_father


def graph():
    if not search_wit():
        logger.info(
            "Tried to show graph but No wit found in this directory!")
    options = {
        'node_color': 'yellow',
        'node_size': 4000,
        'width': 2,
        'edge_color': 'purple'
    }
    graph = nx.DiGraph(**options)
    head, _master, _brancher = get_master_head()
    graph.add_edges_from(get_father_child(head))
    plt.tight_layout()

    nx.draw_networkx(graph, arrows=True, **options)
    plt.show()


def branch(name):
    if not search_wit():
        logger.info(
            "Tried to preform branch, No wit found in this directory!")
    head, master, _brancher = get_master_head()
    update_ref_file(head, name)
    logger.info(f"branch {name} is ready to go!")


def get_branch():
    with open(os.path.join(search_wit(), "activated.txt"), "r") as act:
        cur_act = act.read()
    return cur_act


def find_merging_point(branch):
    head, master, _brancher = get_master_head()
    head = get_father_child(head, True)
    branch = get_father_child(check_all_branches(branch), True)
    for pos_merge in head:
        for pos_merge1 in branch:
            if pos_merge[1] == pos_merge1[1]:
                return pos_merge[1]


def check_merge(merger, branch_name):
    head, _master, _brancher = get_master_head()
    images = search_wit(subfolder="images")
    cur_father = (os.path.join(images, merger))
    cur_head = (os.path.join(images, head))
    cur_stage = (search_wit(subfolder="staging_area"))
    changes = get_diff_files(filecmp.dircmp(cur_head, cur_stage))
    branch_com = (os.path.join(images, check_all_branches(branch_name)))
    if changes != []:
        logger.warning("cant merge, files not the same!")
        return False
    branch_change = get_diff_files(filecmp.dircmp(cur_father, branch_com))
    head_change = get_diff_files(filecmp.dircmp(cur_father, cur_head))
    head_files = get_full_path(cur_head, head_change)
    branch_files = get_full_path(branch_com, branch_change)
    return branch_files, head_files


def get_full_path(from_where, list_of):
    inside = os.listdir(from_where)[0]
    from_where = os.path.join(from_where, inside)
    full_list = []
    for files in list_of:
        for file in files:
            file = (os.path.join(from_where, file))
            full_list.append(f"{file}")
    return full_list


def move_to_merge(files):
    for file in files:
        shutil.copy2(file, search_wit(subfolder="staging_area"))


def merge(branch_name):
    if not search_wit():
        logger.info(
            "Tried to preform merge, No wit found in this directory!")
    merger = find_merging_point(branch_name)
    branch, head = check_merge(merger, branch_name)
    move_to_merge(branch)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.debug("no parameters have been sent to the console!")
    else:
        if sys.argv[1] == "search_wit":
            search_wit()
        if sys.argv[1] == "init":
            init()
        if sys.argv[1] == "add":
            add(sys.argv[2])
        if sys.argv[1] == "commit":
            commit(sys.argv[2])
        if sys.argv[1] == "status":
            status()
        if sys.argv[1] == "checkout":
            checkout(sys.argv[2])
        if sys.argv[1] == "graph":
            graph()
        if sys.argv[1] == "branch":
            branch(sys.argv[2])
        if sys.argv[1] == "merge":
            merge(sys.argv[2])
