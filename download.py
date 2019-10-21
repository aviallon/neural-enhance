from __future__ import print_function
import requests;
import re;
import json;
import time;
import logging;
import urllib;
import urllib2;
import os;
from os.path import exists as file_exists
import timeout_decorator;
import hashlib;
import binascii;
from files import Path
import sys

def flush():
    sys.stdout.flush()

os.chdir("/home/aviallon/git/neural-enhance/")

logging.basicConfig(level=logging.FATAL);
logger = logging.getLogger(__name__)

def create_trainee(keywds, nombre, theme):
    images = []
    nom_dossier = str(Path(str(theme).replace(' ','_') + "_train"))
    try:
        os.mkdir(nom_dossier)
    except Exception as e:
        print("Le dossier existe deja (!)")
    search(keywds, images,nombre,nom_dossier)
    

def search(keywords, images, nombre=15, dossier="."):
    print("=====\nDownload for keywords: {0}\n=====".format(keywords))
    url = 'https://duckduckgo.com/';
    params = {
        'q': keywords
    };

    logger.debug("Hitting DuckDuckGo for Token");

    #   First make a request to above URL, and parse out the 'vqd'
    #   This is a special token, which should be used in the subsequent request
    res = requests.post(url, data=params)
    searchObj = re.search(r'vqd=([\d-]+)\&', res.text, re.M|re.I);

    if not searchObj:
        logger.error("Token Parsing Failed !");
        return -1;

    logger.debug("Obtained Token");

    headers = {
        'dnt': '1',
        'accept-encoding': 'gzip, deflate, sdch, br',
        'x-requested-with': 'XMLHttpRequest',
        'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6,ms;q=0.4',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'referer': 'https://duckduckgo.com/',
        'authority': 'duckduckgo.com',
    }

    params = (
    ('l', 'wt-wt'),
    ('o', 'json'),
    ('q', keywords),
    ('vqd', searchObj.group(1)),
    ('f', ',,,'),
    ('p', '-1'),
    ('iaf', 'size%3Aimagesize-wallpaper%2Ctype%3Aphoto-photo') # for big pictures and photos only filter
    )

    requestUrl = url + "i.js";

    #logger.debug("Hitting Url : %s", requestUrl);
    
    finished = False

    while not(finished):
        while True:
            try:
                res = requests.get(requestUrl, headers=headers, params=params);
                data = json.loads(res.text);
                break;
            except ValueError as e:
                #logger.debug("Hitting Url Failure - Sleep and Retry: %s", requestUrl);
                print("Waiting for connection...")
                time.sleep(3);
                continue;

        #logger.debug("Hitting Url Success : %s", requestUrl);
        
        #printJson(data["results"]);
        saveImages(data["results"],images,dossier,nombre);
        print("Nb images {0}/{1}".format(len(images),nombre))
        if len(images) >= nombre or "next" not in data:
            logger.info("Got everything !");
            downloadImages(dossier,images,keywords)
            finished = True
            return;
        else:
            requestUrl = url + data["next"];
    
nbits = 512

@timeout_decorator.timeout(10)
def _req(start,fin,url):
    req = urllib2.Request(url)
    req.headers['Range'] = 'bytes={0}-{1}'.format(start,fin)
    f = urllib2.urlopen(req)
    return f.read(fin-start)

def urlMD5(url):
    try:
        start = 0; # Has to be zero in case the server doesn't support it...
        fin = start+nbits;
        temp = _req(start,fin,url)
        #print(binascii.hexlify(temp))
        return hashlib.md5(temp).hexdigest()
    except Exception as e:
        return hashlib.md5(b'00000').hexdigest()

def localMD5(chemin):
    try:
        start = 0;
        fin = start+nbits;
        f = open(chemin,'rb')
        f.seek(start,0)
        temp = f.read(fin-start)
        #print(binascii.hexlify(temp))
        return hashlib.md5(temp).hexdigest()
    except Exception as e:
        return hashlib.md5(b'11111').hexdigest()

def saveImages(objs,images,dossier,nombre):
    banlist = "";
    try:
        banlist = open(str(Path(dossier)+"banlist.txt"),'r').read()
    except Exception as e:
        pass;
        
    print("Searching...")
        
    for obj in objs:
        if int(obj["width"]) >= 1024 and int(obj["height"]) >= 720:
            md5remote = urlMD5(obj["image"])
            if md5remote in banlist:
                print('x',end='')
                continue;
            temp = {
                'titlehash': hashlib.md5(obj["title"].encode('utf-8')).hexdigest(),
                'image': obj["image"],
                'hash': md5remote
                }
            images.append(temp)
            print(".",end='');
            flush()
            if(len(images)>=nombre):
                break;

@timeout_decorator.timeout(10)
def downloadImage(url,chemin):
        urllib.urlretrieve(url,chemin) 
            
def downloadImages(dossier,images,keywds):
    print("****")
    banlist = open(str(Path(dossier)+"banlist.txt"),'a')
    for i,img in enumerate(images):
        errorflag = False
        print("Downloading image {0} of {1}...".format(i+1, len(images)),end='');
        flush()
        extension = "unknown";
        if len(re.findall(r'\.jpe?g', img["image"], re.M|re.I)) > 0:
            extension = "jpg"
        elif len(re.findall(r'\.png', img["image"], re.M|re.I)) > 0:
            extension = "png"
        elif len(re.findall(r'\.gif', img["image"], re.M|re.I)) > 0:
            extension = "gif"
        chemin = "{0}/{1}.{2}".format(dossier,img["hash"],extension);
        unmatch = False
        checksum = localMD5(chemin)
        if file_exists(chemin):
            if checksum == img["hash"]:
                print("pass.");
                continue;
            else:
                print("MD5 mismatch (should be {0})! Redownloading...".format(img["hash"]),end='')
                flush()
                unmatch = True
        try:
                downloadImage(str(img["image"]), chemin)                
        except timeout_decorator.TimeoutError as e:
                print(" /!\\ timed out!");
                errorflag=True
        
        if (errorflag or unmatch) and (img["hash"] != localMD5(chemin)):
            banlist.write(img["hash"]+"\n"+checksum+"\n")
            try:
                os.remove(chemin)
            except:
                pass;
            print("fail! - banning.");
        elif not(errorflag):
            print("done.");
        else:
            print("error!");
            
    banlist.close()

n = 1000
create_trainee("test",n,"test")
