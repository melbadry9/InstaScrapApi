#standard modules 
import json
import time
import logging
import traceback
import threading

#third party modules
import tqdm
import requests
from bs4 import BeautifulSoup as bs

#package modules
from .meta import (EXCUTION_ERROR, FAILD_LOGIN, PRIVATE_USER, RATE_LIMIT, OUTPUT, hashes, headers)


#LOGGING
file_name = "{0}.log".format(time.ctime().replace(" ","_").replace(":","-"))
logging.basicConfig(level=logging.DEBUG, filename=file_name,format="%(asctime)s - %(processName)s -%(threadName)s %(levelname)s: %(message)s")


class USER(object):
    '''create instagram user to be scraped

        Parameters
        ----------
        username : str
            instagram username
        cookies : dict 
            valid session cookies
        session: requests.Session
            active requests session
        verbose: bool
            enable debug messages
        bar: bool
            enable progress bar
        timeout: int
            request timeout
        threads: int
            number of running threads
        '''

    # formating the output
    p = OUTPUT()

    def __init__(self, username, cookies=None, session=None, verbose=False, bar=True, timeout=20, threads=5):
        self.info = None
        self.full_info = None
        self.user_valid = None
        self.username = username
        
        self.bar = bar
        self.cookie = cookies
        self.timeout = timeout
        self.verbose = verbose
        self.info_retry_attempts = 10

        self.threads = []
        self.media_list = []
        self.media_error = []
        
        self.following_list = [] 
        self.following_error = []  
        self.following_threads = []

        self.follower_list = []
        self.follower_error = [] 
        self.follower_threads = []

        self.story = None
        self.story_error = []

        if session == None:
            self.session = requests.Session()
        else:
            self.session = session
        self.session.headers = headers
        self.jail = threading.Semaphore(threads)
        
    def Information(self) -> dict:
        '''collecting user basic information

        Returns
        -------
        dict
            dictionary with user profile information
            {
            "errors": [],
            "pref":{
                "id": "",
                "username": "",
                "full_name": "",
                "media": "",
                "followers": "",
                "following": "",
                "profile_picture": {
                    "normal": "",
                    "hd": ""
                },
                "biography": "",
                'private': "",
                "verified": "" 
            },
            "full": {}
            }
        '''
        # checking whether cookies or session are there
        if (self.cookie == None) and (dict(self.session.cookies) == {}):
            msg = "NON_VALID_SESSION"
            logging.error(msg)
            if self.verbose:
                tqdm.tqdm.write(self.p.Error(msg))
            return 

        done = False
        retry_attempts = 0
        query_url = "https://www.instagram.com/%s/?__a=1" % (self.username)
        
        while not done:
            try:
                errors = []
                # whether to use cookies or session
                if self.cookie == None:
                    query_result = self.session.get(query_url, timeout=self.timeout)
                else:
                    query_result = self.session.get(query_url, cookies=self.cookie, timeout=self.timeout)

                # make sure that user is exist  
                if "The link you followed may be broken" in query_result.text:
                    self.user_valid = False
                    errors.append("USER_NOT_FOUND")
                    logging.error("USER_NOT_FOUND <%s>" % self.username)
                    msg = self.p.Error("USER_NOT_FOUND" + self.p.High(self.username))
                    if self.verbose:
                        tqdm.tqdm.write(msg)
                    return {"errors": errors, "pref": "", "full": ""}
                
                if query_result.status_code == 200:
                    # scraping pref data from json response
                    profile_page = query_result.json()['graphql']['user']
                    profile_id = profile_page['id']
                    profile_full_name = profile_page['full_name']
                    profile_node_number = profile_page['edge_owner_to_timeline_media']['count']
                    profile_following = profile_page['edge_follow']['count']
                    profile_follwers = profile_page['edge_followed_by']['count']
                    profile_pic = profile_page['profile_pic_url']
                    profile_pic_hd = profile_page['profile_pic_url_hd']
                    profile_biography = profile_page['biography']
                    profile_security = profile_page['is_private']
                    profile_is_verified = profile_page['is_verified']
                    followed_by_viewer = profile_page['followed_by_viewer']
                else:
                    raise(RATE_LIMIT)

                # make sure account is not private or followed by the viewer
                if (profile_security == True) and (followed_by_viewer == False):
                        if not profile_id == dict(self.session.cookies)['ds_user_id']:
                            errors.append("PRIVATE_USER")
                            logging.error("<%s> PRIVATE_USER" % self.username)
                            msg = self.p.Error("PRIVATE_USER" + self.p.High(self.username))
                            if self.verbose:
                                tqdm.tqdm.write(msg)
                            
                # generate user pref data
                pref_data = {
                    "id": profile_id,
                    "username": self.username,
                    "full_name": profile_full_name,
                    "media": profile_node_number,
                    "followers": profile_follwers,
                    "following": profile_following,
                    "profile_picture": {
                        "normal": profile_pic,
                        "hd": profile_pic_hd
                    },
                    "biography": profile_biography,
                    'private': profile_security,
                    "verified": profile_is_verified 
                }

                logging.info("<%s> profile scraped successfuly" % self.username)
                msg = self.p.Success("profile scraped successfuly" + self.p.High(self.username))
                if self.verbose:
                    tqdm.tqdm.write(msg)

                # the final data
                data = {
                    "errors": errors,
                    "pref": pref_data,
                    "full": profile_page
                }

                # to get out the loop
                done = True
                self.user_valid = True

            except RATE_LIMIT:
                msg = "RATE_LIMITED [information]"
                logging.error(msg)
                if self.verbose:
                    tqdm.tqdm.write(self.p.Error(msg))
                time.sleep(30)
            
            except Exception as e:

                retry_attempts += 1
                msg = "{0}\n{1}".format(e, traceback.format_exc())
                
                logging.error(msg)
                if self.verbose:
                    tqdm.tqdm.write(self.p.Error(msg))

                # handle max faild retries 
                if retry_attempts > self.info_retry_attempts:
                    errors.append("MAX_RETRIES")
                    logging.error("MAX_RETRIES <%s>" % self.username)

                    msg = self.p.Error("MAX_RETRIES" + self.p.High(self.username))
                    if self.verbose:
                        tqdm.tqdm.write(msg)
                    
                    # empty data
                    data = {
                        "errors": errors,
                        "pref": "",
                        "full": ""
                        }

                    # to get out the loop
                    done = True

        # set object data
        self.info = data['pref']
        self.full_info = data['full']
        return data

    def Media(self, get_number=0, per_request=50, after="") -> dict:
        ''' collecting user media 

        Parameters
        ----------
        get_number : int
            number of media to scrap (default all)
        per_request : int
            number of media each request (default 50)
        after : str
            represent instagram cursor of last media

        Returns
        -------
        dict
            dictionary with media and time elapsed
            {
            "errors": [],
            "media": {
                "count": 0,
                "data": []
            },
            "time": 2
            }    
        '''

        if not self.user_valid:
            msg = "NOT_VALID_USERNAME"
            logging.error("{0} <{1}>".format(msg,self.username))
            if self.verbose:
                tqdm.tqdm.write(self.p.Error(msg) + self.p.High(self.username))
            return

        time1 = time.time()
        profile_id = self.info['id']

        # whether to get specefic number of media or all of them
        if get_number == 0:
            nodes_number = self.info['media']
        else:
            nodes_number = get_number
        
        
        msg = "media number set to: "
        logging.debug(msg + str(nodes_number))
        if self.verbose:
            tqdm.tqdm.write(self.p.Debug(msg) + self.p.High(str(nodes_number)))


        # init progress bar
        if self.bar:
            media_progress = tqdm.trange(nodes_number, unit=" Node @ "+self.username, leave=False, ascii=True)
            media_progress.refresh(True)
        else:
            media_progress = None

        # used to decide the next thread options
        next_options = self.__ParseVar(nodes_number, per_request)

        # start scraping media
        self.__GetMedia(profile_id=profile_id,after=after, options=next_options, bar=media_progress, username=self.username)
        while True:
            # wait until every thread is done scraping media
            for item in self.threads:
                if item.is_alive():
                    continue
                else:
                    try:
                        self.threads.remove(item)
                    except ValueError:
                        continue
            
            # end the loop
            if len(self.threads) == 0:
                break 
        
        logging.info("profile media scraped successfuly <{0}>".format(self.username))
        msg = "profile media scraped successfuly {0}".format(self.p.High(self.username))
        if self.verbose:
            tqdm.tqdm.write(self.p.Success(msg))


        time2 = time.time()
        if self.bar:
            media_progress.close()
        # FINAL DATA
        data = {
            "errors": self.media_error,
            "media": {
                "count": len(self.media_list),
                "data": self.media_list
            },
            "time": time2-time1
        }

        return data

    def __GetMedia(self, profile_id: int, after: str, options: list, bar, username:str="") -> None:

        with self.jail:
            done = False
            has_next = None
            query_hash_pic = hashes['profile_media']

            # check whether start scraping or return
            if options[0] == 1:
                has_next = False
                number = options[1]
            elif options[0] == 0:
                return
            else:
                has_next == True
                number = options[2]
                
            
            while not done:
                try:
                    query_url = 'https://www.instagram.com/graphql/query/?query_hash=%s&variables={"id":%s,"first":%s,"after":"%s"}' % (query_hash_pic, str(profile_id), number, after)
                    query_result = self.session.get(query_url, timeout=self.timeout)
                    query_json = json.loads(query_result.text)
                    
                    try:
                        user = query_json['data']['user']['edge_owner_to_timeline_media']
                        has_next = user['page_info']["has_next_page"]
                        after_that = user['page_info']['end_cursor']
                    except KeyError:
                        raise(RATE_LIMIT)
                    
                    status = query_json['status']
                    if status == "ok":
                        if has_next == True:
                            options[0] -= 1 
                            runing_thread = threading.Thread(target=self.__GetMedia,args=(profile_id, after_that, options, bar))
                            runing_thread.start()
                            self.threads.append(runing_thread)
                        self.__ScrapMedia(user, bar=bar)
                    done = True
            
                except RATE_LIMIT:
                    self.media_error.append("RATE_LIMITED [media] <%s>" % str(profile_id))
                    logging.error("<%s> RATE_LIMITED" % username)
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("RATE_LIMITED [media]" + self.p.High(self.username)))
                    time.sleep(30)

                except Exception as e:
                    if not e in self.media_error:
                        self.media_error.append(str(e).upper())
                        logging.error("%s \n %s" % (e,traceback.format_exc()))
                        if self.verbose:
                            tqdm.tqdm.write(self.p.Error(str(e).upper()))

    def __ScrapMedia(self, user:dict, bar) -> None:
        nodess = user['edges']
        for nodes in nodess:
            node_done = False
            nodes = nodes['node']
            while not node_done:
                # MEDIA_DATA
                node_id = nodes['id']
                node_type = nodes['__typename']
                node_code = nodes['shortcode']
                owner = nodes['owner']['id']
                try:
                    caption = nodes['edge_media_to_caption']['edges'][0]['node']['text']
                except IndexError:
                    caption = ""
                node_comment_count = nodes['edge_media_to_comment']['count']
                node_like_count = nodes['edge_media_preview_like']['count']
                taken_at = nodes['taken_at_timestamp']
                node_is_video = nodes['is_video']
                dimentions = nodes['dimensions']
                comments_disabled = nodes['comments_disabled']
                nodes_links = nodes['thumbnail_resources']
                gating_info = nodes['gating_info']

                # GET SIDECAR ALL MEDIA
                if node_type == "GraphSidecar":
                    node_sidecar_done = False
                    while not node_sidecar_done:
                        try:
                            sidecar_page_url = "https://www.instagram.com/p/%s" % (node_code)
                            sidecar_html = self.session.get(sidecar_page_url, timeout=self.timeout)
                            try:
                                sidecar_result_html = bs(sidecar_html.content, "lxml").findAll("script")[3].text
                                sidecar_result_json = json.loads(sidecar_result_html.split("Data =")[1].replace(";", ""))
                            except IndexError:
                                sidecar_result_html = bs(sidecar_html.content, "lxml").findAll("script")[4].text
                                sidecar_result_json = json.loads(sidecar_result_html.split("Data =")[1].replace(";", ""))

                            sidecar_media = sidecar_result_json['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
                            for sidecar_nodes in sidecar_media:
                                sidecar_nodes = sidecar_nodes['node']
                                # MEDIA_DATA
                                node_id = sidecar_nodes['id']
                                node_type = sidecar_nodes['__typename']
                                node_code = sidecar_nodes['shortcode']
                                node_is_video = sidecar_nodes['is_video']
                                dimentions = sidecar_nodes['dimensions']
                                nodes_links = sidecar_nodes['display_resources']
                                gating_info = sidecar_nodes['gating_info']
                                node_download_link = sidecar_nodes['display_url']
                                node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                            taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                            node_download_link]
                                node_db = {
                                    "node_id": node_db[0],
                                    "type": node_db[1],
                                    "code": node_db[2],
                                    "owner": node_db[3],
                                    "caption": node_db[4],
                                    "comments_number": node_db[5],
                                    "likes_number": node_db[6],
                                    "taken_time": node_db[7],
                                    "video": node_db[8],
                                    "dimentions": node_db[9],
                                    "comments_disabled": node_db[10],
                                    "links": node_db[11],
                                    "gating_info": node_db[12],
                                    "hd_link": node_db[13]
                                }
                                if node_db not in self.media_list:
                                    self.media_list.append(node_db)
                            node_sidecar_done = True
                        except Exception as e:
                            logging.error("%s \n %s" % (e,traceback.format_exc()))
                            if self.verbose:
                                tqdm.tqdm.write(self.p.Error(str(e).upper()))
                            continue

                # GET VIDEO
                elif node_is_video:
                    node_video_done = False
                    while not node_video_done:
                        try:
                            video_page_url = "https://www.instagram.com/p/%s" % (node_code)
                            video_html = self.session.get(video_page_url, timeout=self.timeout).text
                            video_page = bs(video_html, "lxml").find("meta", {"property": "og:video:secure_url"})
                            node_download_link = video_page['content']
                            node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                        taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                        node_download_link]
                            node_db = {
                                "node_id": node_db[0],
                                "type": node_db[1],
                                "code": node_db[2],
                                "owner": node_db[3],
                                "caption": node_db[4],
                                "comments_number": node_db[5],
                                "likes_number": node_db[6],
                                "taken_time": node_db[7],
                                "video": node_db[8],
                                "dimentions": node_db[9],
                                "comments_disabled": node_db[10],
                                "links": node_db[11],
                                "gating_info": node_db[12],
                                "hd_link": node_db[13]
                            }
                            if node_db not in self.media_list:
                                self.media_list.append(node_db)
                            node_video_done = True
                        except Exception as e:
                            logging.error("%s \n %s" % (e,traceback.format_exc()))
                            if self.verbose:
                                tqdm.tqdm.write(self.p.Error(str(e).upper()))
                            continue

                # GET PIC
                else:
                    node_download_link = nodes['display_url']
                    node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                node_download_link]
                    node_db = {
                        "node_id": node_db[0],
                        "type": node_db[1],
                        "code": node_db[2],
                        "owner": node_db[3],
                        "caption": node_db[4],
                        "comments_number": node_db[5],
                        "likes_number": node_db[6],
                        "taken_time": node_db[7],
                        "video": node_db[8],
                        "dimentions": node_db[9],
                        "comments_disabled": node_db[10],
                        "links": node_db[11],
                        "gating_info": node_db[12],
                        "hd_link": node_db[13]
                    }
                    if node_db not in self.media_list:
                        self.media_list.append(node_db)
                node_done = True
                if self.bar:
                    bar.update(1)

    def Following(self, get_number=0, per_request=50, after="") -> dict:
        '''collecting user following list 

        Parameters
        ----------
        get_number : int
            number of following to scrap (default 0 == all)
        per_request : int
            number of following each request (default 50)
        after : str
            represent instagram cursor of last following
        
        Returns
        -------
        dict
            dictionary with following and time elapsed
            {
            "errors": following_error,
            "following": {
                "count": len(following_list),
                "data": following_list
            },
            "time": time2-time1
            }
        '''

        if not self.user_valid:
            msg = "NOT_VALID_USERNAME"
            logging.error("{0} <{1}>".format(msg,self.username))
            if self.verbose:
                tqdm.tqdm.write(self.p.Error(msg) + self.p.High(self.username))
            return

        time1 = time.time()
        username = self.info['username']
        profile_id = self.info['id']

        if get_number == 0:
            followings_number = self.info['following']
        else:
            followings_number = get_number

        msg = "following number set to: "
        logging.debug(msg + str(followings_number))
        if self.verbose:
            tqdm.tqdm.write(self.p.Debug(msg) + self.p.High(str(followings_number)))

        if self.bar:
            following_progress = tqdm.trange(followings_number, unit=" following @ " + self.username, leave=False, ascii=True)
            following_progress.refresh(True)
        else:
            following_progress = None

        next_options = self.__ParseVar(followings_number, per_request)

        self.__GetFollowing(profile_id=profile_id, after=after, options=next_options, bar=following_progress, username=username)
        while True:
            for item in self.following_threads:
                if item.is_alive():
                    pass
                else:
                    self.following_threads.remove(item)
            
            if len(self.following_threads) == 0:
                break 
        
        logging.info("profile following scraped successfuly <{0}>".format(self.username))
        msg = "profile following scraped successfuly {0}".format(self.p.High(self.username))
        if self.verbose:
            tqdm.tqdm.write(self.p.Success(msg))

        time2 = time.time()
        if self.bar:
            following_progress.close()

        data = {
            "errors": self.following_error,
            "following": {
                "count": len(self.following_list),
                "data": self.following_list
            },
            "time": time2-time1
        }
        
        return data

    def __GetFollowing(self, profile_id: int, after: str, options: list, bar, username:str="") -> None:
        with self.jail:

            done = False
            has_next = None
            query_hash_following = hashes['profile_following']
            
            if options[0] == 1:
                has_next = False
                number = options[1]
            elif options[0] == 0:
                return
            else:
                has_next == True
                number = options[2]
            
            while not done:
                try:
                    query_url = 'https://www.instagram.com:443/graphql/query/?query_hash=%s&variables={"id":%s,"first":%s,"after":"%s"}' % (query_hash_following, profile_id, number, after)
                    query_result = self.session.get(query_url, timeout=self.timeout)
                    query_json = json.loads(query_result.text)
                    status = query_json['status']

                    if status == "ok":
                        followings = query_json['data']['user']['edge_follow']
                        has_next = followings['page_info']['has_next_page']
                        after_that = followings['page_info']['end_cursor']
                    
                        if has_next == True:
                            options[0] -= 1
                            following_thread = threading.Thread(target=self.__GetFollowing,args=(profile_id, after_that, options, bar))
                            following_thread.start()
                            self.following_threads.append(following_thread)
                        self.__ScrapFollowing(followings['edges'], bar=bar)  
                    else:
                        raise RATE_LIMIT
                    done = True  

                except PRIVATE_USER:
                    self.following_error.append("PRIVATE_USER")
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("PRIVATE_USER"))
                    return


                except RATE_LIMIT:
                    self.following_error.append("RATE_LIMITED")
                    logging.error("RATE_LIMITED [following]")
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("RATE_LIMITED [following]"))
                    time.sleep(30)

                except Exception as e:
                    if e not in self.following_error:
                        self.following_error.append(e)
                        logging.error(" %s \n %s " % (e,traceback.format_exc()))
                        if self.verbose:
                            tqdm.tqdm.write(self.p.Error(str(e).upper()))
                    
    def __ScrapFollowing(self, followings: dict, bar) -> None:
        for user in followings:
            node = user['node']
            userid = node['id']
            username = node['username']
            full_name = node['full_name']
            profile_pic_small = node['profile_pic_url']
            is_verified = node['is_verified']
            viewer_following_user = node['followed_by_viewer']
            viewer_requested = node['requested_by_viewer']
            data = {
                "id": userid,
                "username": username,
                "full_name": full_name,
                "small_pic": profile_pic_small,
                "verified": is_verified,
                "following_user": viewer_following_user,
                "requested_by_viewer": viewer_requested
            }
            self.following_list.append(data)
            if self.bar:
                bar.update(1)

    def Follower(self, get_number=0, per_request=50, after="") -> dict:
        '''collecting user follower list 

        Parameters
        ----------
        get_number : int
            number of follower to scrap (default 0 == all)
        per_request : int
            number of follower each request (default 50)
        after : str
            represent instagram cursor of last follower
        
        Returns
        -------
        dict
            dictionary with following and time elapsed
            {
            "errors": follower_error,
            "following": {
                "count": len(follower_list),
                "data": follower_list
            },
            "time": time2-time1
            }
        '''

        if not self.user_valid:
            msg = "NOT_VALID_USERNAME"
            logging.error("{0} <{1}>".format(msg,self.username))
            if self.verbose:
                tqdm.tqdm.write(self.p.Error(msg) + self.p.High(self.username))
            return

        time1 = time.time()
        username = self.info['username']
        profile_id = self.info['id']

        if get_number == 0:
            follower_number = self.info['followers']
        else:
            follower_number = get_number

        msg = "follower number set to: "
        logging.debug(msg + str(follower_number))
        if self.verbose:
            tqdm.tqdm.write(self.p.Debug(msg) + self.p.High(str(follower_number)))
        
        if self.bar:
            follower_progress = tqdm.trange(follower_number, unit=" follower @ " + self.username, leave=False, ascii=True)
            follower_progress.refresh(True)
        else:
            follower_progress = None

        next_options = self.__ParseVar(follower_number, per_request)

        self.__GetFollower(profile_id=profile_id, after=after, options=next_options, bar=follower_progress, username=username)
        while True:
            for item in self.follower_threads:
                if item.is_alive():
                    pass
                else:
                    self.follower_threads.remove(item)
            
            if len(self.follower_threads) == 0:
                break 

        logging.info("profile follower scraped successfuly <{0}>".format(self.username))
        msg = "profile follower scraped successfuly {0}".format(self.p.High(self.username))
        if self.verbose:
            tqdm.tqdm.write(self.p.Success(msg))
        
        time2 = time.time()
        if self.bar:
            follower_progress.close()
        
        data = {
            "errors": self.follower_error,
            "following": {
                "count": len(self.follower_list),
                "data": self.follower_list
            },
            "time": time2-time1
        }  
        return data

    def __GetFollower(self, profile_id: int, after: str, options: list, bar, username:str=""):
        with self.jail:
            done = False
            has_next = None
            query_hash_follower = hashes['profile_follower']
            if options[0] == 1:
                has_next = False
                number = options[1]
            elif options[0] == 0:
                return
            else:
                has_next == True
                number = options[2]
            
            while not done:
                try:
                    query_url = 'https://www.instagram.com:443/graphql/query/?query_hash=%s&variables={"id":%s,"first":%s,"after":"%s"}' % (query_hash_follower, profile_id, number, after)
                    query_result = self.session.get(query_url, timeout=15)
                    query_json = json.loads(query_result.text)
                    status = query_json['status']

                    if status == "ok":
                        followers = query_json['data']['user']['edge_followed_by']
                        has_next = followers['page_info']['has_next_page']
                        after_that = followers['page_info']['end_cursor']
                    
                        if has_next == True:
                            options[0] -= 1
                            follower_thread = threading.Thread(target=self.__GetFollower,args=(profile_id, after_that, options, bar))
                            follower_thread.start()
                            self.follower_threads.append(follower_thread)
                        self.__ScrapFollower(followers['edges'], bar=bar)  
                    else:
                        raise RATE_LIMIT

                    done = True  

                except PRIVATE_USER:
                    self.follower_error.append("PRIVATE_USER")
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("PRIVATE_USER"))

                except RATE_LIMIT:
                    self.follower_error.append("RATE_LIMITED")
                    logging.error("RATE_LIMITED [follower]")
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("RATE_LIMITED [follower]"))
                    time.sleep(30)

                except Exception as e:
                    if e not in self.follower_error:
                        self.follower_error.append(e)
                        logging.error(" %s \n %s " % (e,traceback.format_exc()))
                        if self.verbose:
                            tqdm.tqdm.write(self.p.Error(str(e)))

    def __ScrapFollower(self, followers: dict, bar):

        for user in followers:
            node = user['node']
            userid = node['id']
            username = node['username']
            full_name = node['full_name']
            profile_pic_small = node['profile_pic_url']
            is_verified = node['is_verified']
            viewer_following_user = node['followed_by_viewer']
            viewer_requested = node['requested_by_viewer']
            data = {
                "id": userid,
                "username": username,
                "full_name": full_name,
                "small_pic": profile_pic_small,
                "verified": is_verified,
                "following_user": viewer_following_user,
                "requested_by_viewer": viewer_requested
            }
            self.follower_list.append(data)
            if self.bar:
                bar.update(1)

    def Story(self) -> dict:
        ''' getting user stories 

        Returns
        -------
        dict
            users stories
            {
            "errors": []],
            "stories": {},
            "time": 0
            }
        '''
        # INIT VARIABLES
        json_type = json.dumps([self.info['id']])
        query_hash_story = hashes['story']
        time1 = time.time()

        try:
            query_url = 'https://www.instagram.com/graphql/query/?query_hash=%s&variables={"reel_ids":%s,"precomposed_overlay":false}' % (query_hash_story, json_type)
            query_result = self.session.get(query_url).text
            query_json = json.loads(query_result)
            all_users = query_json['data']['reels_media']
            for user in all_users:
                latest_story = user['latest_reel_media']
                end_at = user['expiring_at']
                seen = user['seen']
                stories = user['items']
                username = user['user']['username']
                story_data = {
                    "username": username,
                    "last_story": latest_story,
                    "end": end_at,
                    "seen": seen,
                    "stories": stories
                }
                self.story = story_data

        except KeyError:
            pass

        except Exception as e:
            self.story_error.append(e)
            logging.error(str(e).upper())
            if self.verbose:
                tqdm.tqdm.write(self.p.Error((str(e).upper())))

        logging.info("profile story scraped successfuly <{0}>".format(self.username))
        msg = "profile story scraped successfuly {0}".format(self.p.High(self.username))
        if self.verbose:
            tqdm.tqdm.write(self.p.Success(msg))

        time2 = time.time()
        # FINAL DATA
        try: 
            c = len(self.story['stories'])
        except TypeError:
            c = 0 

        data = {
            "errors": self.story_error,
            "stories": {
                "count": c,
                'data': self.story
            },
            "time": time2-time1
        }
        
        return data

    def LogIn(self, username: str, password: str) -> requests.Session:
        '''get user cookie using username and password
        Parameters
        ----------
        username : str
            instagram username, mail or mobile
        password : str 
            account password

        Returns
        -------
        requests.Session
        '''
        url = "https://www.instagram.com:443/accounts/login/ajax/"
        headers = {
            "User-Agent": "Mozilla/6.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "X-CSRFToken": "gTk1sqtecdVkbDeVN7IJl90epedNRIRm",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        }

        data = {
            "username": username,
            "password": password,
            "queryParams": "{\"source\":\"auth_switcher\"}"
        }

        # RESPONSE
        try:
            session = requests.Session()
            session.headers = headers
            query_result = session.post(url, data=data)
        except Exception:
            logging.error("faild to login .. check you connectivity")
            if self.verbose:
                tqdm.tqdm.write(self.p.Error("faild to login .. check you connectivity"))
            return

        # EXTRACT USER_ID AND COOKIES
        try:
            json.loads(query_result.text)['userId']
        except KeyError:
            logging.warning("WRONG_CRED")
            tqdm.tqdm.write(self.p.Error("WRONG_CRED"))
            return

        logging.info("session created")
        if self.verbose:
            tqdm.tqdm.write(self.p.Success("session created"))
        self.session = session
        return session

    @staticmethod
    def __ParseVar(var: int, per_request=50) -> list:
        '''used for calculate number of requests depending on per_request and number

        Parameters
        ----------
        var : int
            number of items
        per_request : int
            number of items per request default=50
        
        Returns
        -------
        list
            [number_or_requests, number_of_left, per_request]
        '''
        if var > per_request:
            request_number = var // per_request
            request_number_left = var % per_request
            if request_number_left > 0:
                request_number += 1
            else:
                request_number = request_number
        else:
            request_number = 1
            request_number_left = var

        return [request_number, request_number_left, per_request]


class ROOT(USER):
    '''create instagram root user (viewer) to be scraped

        Parameters
        ----------
        username : str
            instagram username
        cookies : dict 
            valid session cookies
        session: requests.Session
            active requests session
        verbose: bool
            enable debug messages
        bar: bool
            enable progress bar
        timeout: int
            request timeout
        threads: int
            number of running threads
        '''

    def __init__(self, username, cookies=None, session=None, verbose=False, bar=True, timeout=20, threads=5):
        super().__init__(username, cookies, session, verbose, bar, timeout, threads)

        self.alerts = None
        self. notification_error = []

        self.explore_list = []
        self.explore_error = []
        self.explore_threads = []

    def Notifcation(self) -> dict:
        ''' getting root user notifcation and follow request 

        Returns
        -------
        dict
            dictionary of notfication and follow requests
            {
            "errors": errors,
            "following_request": {},
            "notifcation": {},
            "timestamp": 0,
            "time": 0
            } 
        '''
        
        time1 = time.time()
        try:
            query_url = "https://www.instagram.com:443/accounts/activity/?__a=1"
            query_result = self.session.get(query_url, timeout=self.timeout)
            query_json = json.loads(query_result.text)
            result = query_json['graphql']['user']
            follow_requests = result['edge_follow_requests']['edges']
            follow_requests_count = len(follow_requests)
            noti = result['activity_feed']['edge_web_activity_feed']['edges']
            noti_count = result['activity_feed']['edge_web_activity_feed']['count']
            timestamp = result['activity_feed']['timestamp']
        except Exception as e:
            follow_requests_count = 0
            follow_requests = []
            noti_count = 0
            timestamp = ""
            noti = 0
            self.notification_error.append(e)

        time2 = time.time()

        # FINAL DATA
        data = {
            "errors": self.notification_error,
            "following_request": {
                "count": follow_requests_count, 
                "requests": follow_requests
                },
            "notifcation": {
                "count": noti_count,
                "noti": noti
            },
            "timestamp": timestamp,
            "time": time2 - time1
        }
        self.alerts = data
        return data

    def Search(self, query: str) -> dict:
        '''search for keyword and get the result media
        
        Parameters
        ----------
        query : str
            keyword to search

        Returns
        -------
        dict
        '''
        query_url = "https://www.instagram.com/web/search/topsearch/?context=blended&query=%s" % query
        query_result = self.session.get(query_url, timeout=self.timeout).json()
        return query_result

    def HashTag(self, tag: str, get_number=50, after="") -> dict:
        '''search for hashtag and get the result media
        
        Parameters
        ----------
        tag : str
            keyword to search
        get_number : int
            number of media to get (default 50)
        after : str
            represent instagram cursor of last hashtag

        Returns
        -------
        dict
        '''
        query_hash_hashtag = hashes['hash_tag']
        query_url = 'https://www.instagram.com/graphql/query/?query_hash=%s&variables={"tag_name":"%s","first":%s,"after":"%s"}' % (query_hash_hashtag, tag, get_number, after)
        query_result = self.session.get(query_url, timeout=self.timeout).json()
        return query_result

    def ExploreMedia(self, get_number=14, per_request=14, after="1") -> dict:
        ''' collecting root user explore media 
        
        Parameters
        ----------
        get_number : int
            number of media to scrap (default 14)
        per_request : int
            number of media each request (default 14)
        after : str
            represent instagram cursor of last media (default '1')

        Returns
        -------
        dict
            dictionary with media and time elapsed
            {
            "errors": [],
            "media": {},
            "time": 2
            } 
        '''

        if not self.user_valid:
            msg = "NOT_VALID_USERNAME"
            logging.error("{0} <{1}>".format(msg,self.username))
            if self.verbose:
                tqdm.tqdm.write(self.p.Error(msg) + self.p.High(self.username))
            return
        
        time1 = time.time()
        nodes_number = get_number

        msg = "explore media number set to: "
        logging.debug(msg + str(nodes_number))
        if self.verbose:
            tqdm.tqdm.write(self.p.Debug(msg) + self.p.High(str(nodes_number)))


        #INIT PROGRESS BAR 
        if self.bar:
            explore_progress = tqdm.trange(nodes_number, unit=" Node @ Explore "+self.username, leave=False, ascii=True)
            explore_progress.refresh(True)
        else:
            explore_progress = None

        # CALULATE HOW MANY REQUEST TO MAKE DEFAULT IS 50 PIC PER REQUEST
        next_options = self._USER__ParseVar(nodes_number, per_request)

        # START COLLECTING MEDIA FOR EACH REQUEST
        self.__GetExploreMedia(after=after, options=next_options, bar=explore_progress, username=self.username)
        while True:
            for item in self.explore_threads:
                if item.is_alive():
                    pass
                else:
                    try:
                        self.explore_threads.remove(item)
                    except ValueError:
                        pass
            
            if len(self.explore_threads) == 0:
                break 

        logging.info("profile explore media scraped successfuly <{0}>".format(self.username))
        msg = "profile explore media scraped successfuly {0}".format(self.p.High(self.username))
        if self.verbose:
            tqdm.tqdm.write(self.p.Success(msg))


        time2 = time.time()
        if self.bar:
            explore_progress.close()
        # FINAL DATA
        data = {
            "errors": self.explore_error,
            "media": {
                "count": len(self.explore_list),
                "data": self.explore_list
            },
            "time": time2-time1
        }
        return data

    def __GetExploreMedia(self, after: str, options: list, bar, username:str="") -> None:
        with self.jail:
            done = False
            has_next = None
            query_hash_pic = hashes['explore']

            # check whether start scraping or return
            if options[0] == 1:
                has_next = False
                number = options[1]
            elif options[0] == 0:
                return
            else:
                has_next == True
                number = options[2]
                
            
            while not done:
                try:
                    query_url = 'https://www.instagram.com/graphql/query/?query_hash=%s&variables={"first":%s,"after":"%s"}' % (query_hash_pic, number, after)
                    query_result = self.session.get(query_url, timeout=self.timeout)
                    query_json = json.loads(query_result.text)
                    try:
                        user = query_json['data']['user']['edge_web_discover_media']
                        has_next = user['page_info']["has_next_page"]
                        after_that = user['page_info']['end_cursor']
                    except KeyError:
                        raise(RATE_LIMIT)
                    
                    status = query_json['status']
                    if status == "ok":
                        if has_next == True:
                            options[0] -= 1 
                            runing_thread = threading.Thread(target=self.__GetExploreMedia,args=(after_that, options, bar))
                            runing_thread.start()
                            self.explore_threads.append(runing_thread)
                        self.__ScrapExploreNode(user, bar=bar)
                    done = True
            
                except RATE_LIMIT:
                    self.explore_error.append("RATE_LIMITED")
                    logging.error("RATE_LIMITED [explore]")
                    if self.verbose:
                        tqdm.tqdm.write(self.p.Error("RATE_LIMITED [explore]" + self.p.High(self.username)))
                    time.sleep(30)

                except Exception as e:
                    if not e in self.explore_error:
                        self.explore_error.append(str(e).upper())
                        logging.error("%s \n %s" % (e,traceback.format_exc()))
                        if self.verbose:
                            tqdm.tqdm.write(self.p.Error(str(e).upper()))

    def __ScrapExploreNode(self, user: dict, bar) -> None :
        nodess = user['edges']
        for nodes in nodess:
            node_done = False
            nodes = nodes['node']
            while not node_done:
                # MEDIA_DATA
                node_id = nodes['id']
                node_type = nodes['__typename']
                node_code = nodes['shortcode']
                owner = nodes['owner']['id']
                try:
                    caption = nodes['edge_media_to_caption']['edges'][0]['node']['text']
                except IndexError:
                    caption = ""
                node_comment_count = nodes['edge_media_to_comment']['count']
                node_like_count = nodes['edge_media_preview_like']['count']
                taken_at = nodes['taken_at_timestamp']
                node_is_video = nodes['is_video']
                dimentions = nodes['dimensions']
                comments_disabled = nodes['comments_disabled']
                nodes_links = nodes['thumbnail_resources']
                try:
                    gating_info = nodes['gating_info']
                except:
                    gating_info = None

                # GET SIDECAR ALL MEDIA
                if node_type == "GraphSidecar":
                    node_sidecar_done = False
                    while not node_sidecar_done:
                        try:
                            sidecar_page_url = "https://www.instagram.com/p/%s" % (
                                node_code)
                            sidecar_html = self.session.get(sidecar_page_url,   timeout=self.timeout)
                            try:
                                sidecar_result_html = bs(sidecar_html.content, "lxml").findAll("script")[3].text
                                sidecar_result_json = json.loads(sidecar_result_html.split("Data =")[1].replace(";", ""))
                            except IndexError:
                                sidecar_result_html = bs(sidecar_html.content, "lxml").findAll("script")[4].text
                                sidecar_result_json = json.loads(sidecar_result_html.split("Data =")[1].replace(";", ""))

                            sidecar_media = sidecar_result_json['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
                            for sidecar_nodes in sidecar_media:
                                sidecar_nodes = sidecar_nodes['node']
                                # MEDIA_DATA
                                node_id = sidecar_nodes['id']
                                node_type = sidecar_nodes['__typename']
                                node_code = sidecar_nodes['shortcode']
                                node_is_video = sidecar_nodes['is_video']
                                dimentions = sidecar_nodes['dimensions']
                                nodes_links = sidecar_nodes['display_resources']
                                gating_info = sidecar_nodes['gating_info']
                                node_download_link = sidecar_nodes['display_url']
                                node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                            taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                            node_download_link]
                                node_db = {
                                    "node_id": node_db[0],
                                    "type": node_db[1],
                                    "code": node_db[2],
                                    "owner": node_db[3],
                                    "caption": node_db[4],
                                    "comments_number": node_db[5],
                                    "likes_number": node_db[6],
                                    "taken_time": node_db[7],
                                    "video": node_db[8],
                                    "dimentions": node_db[9],
                                    "comments_disabled": node_db[10],
                                    "links": node_db[11],
                                    "gating_info": node_db[12],
                                    "hd_link": node_db[13]
                                }
                                if node_db not in self.explore_list:
                                    self.explore_list.append(node_db)
                            node_sidecar_done = True
                        except Exception as e:
                            logging.error("%s \n %s" % (e,traceback.format_exc()))
                            if self.verbose:
                                tqdm.tqdm.write(self.p.Error(str(e).upper()))
                            continue

                # GET VIDEO
                elif node_is_video:
                    node_video_done = False
                    while not node_video_done:
                        try:
                            video_page_url = "https://www.instagram.com/p/%s" % (node_code)
                            video_html = self.session.get(video_page_url,   timeout=self.timeout).text
                            video_page = bs(video_html, "lxml").find("meta", {"property": "og:video:secure_url"})
                            node_download_link = video_page['content']
                            node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                        taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                        node_download_link]
                            node_db = {
                                "node_id": node_db[0],
                                "type": node_db[1],
                                "code": node_db[2],
                                "owner": node_db[3],
                                "caption": node_db[4],
                                "comments_number": node_db[5],
                                "likes_number": node_db[6],
                                "taken_time": node_db[7],
                                "video": node_db[8],
                                "dimentions": node_db[9],
                                "comments_disabled": node_db[10],
                                "links": node_db[11],
                                "gating_info": node_db[12],
                                "hd_link": node_db[13]
                            }
                            if node_db not in self.explore_list:
                                self.explore_list.append(node_db)
                            node_video_done = True
                        except Exception as e:
                            logging.error("%s \n %s" % (e,traceback.format_exc()))
                            if self.verbose:
                                tqdm.tqdm.write(self.p.Error(str(e).upper()))
                            continue

                # GET PIC
                else:
                    node_download_link = nodes['display_url']
                    node_db = [node_id, node_type, node_code, owner, caption, node_comment_count, node_like_count,
                                taken_at, node_is_video, dimentions, comments_disabled, nodes_links, gating_info,
                                node_download_link]
                    node_db = {
                        "node_id": node_db[0],
                        "type": node_db[1],
                        "code": node_db[2],
                        "owner": node_db[3],
                        "caption": node_db[4],
                        "comments_number": node_db[5],
                        "likes_number": node_db[6],
                        "taken_time": node_db[7],
                        "video": node_db[8],
                        "dimentions": node_db[9],
                        "comments_disabled": node_db[10],
                        "links": node_db[11],
                        "gating_info": node_db[12],
                        "hd_link": node_db[13]
                    }
                    if node_db not in self.explore_list:
                        self.explore_list.append(node_db)
                node_done = True
                if self.bar:
                    bar.update(1)
 