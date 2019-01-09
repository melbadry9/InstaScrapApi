import sys


os_windows = sys.platform.startswith('win')

if os_windows:
    G = '\033[92m'  # green
    H = '\033[97m'  # high
    B = '\033[94m'  # blue
    R = '\033[91m'  # red
    W = '\033[0m'   # white
    try:
        import win_unicode_console , colorama
        win_unicode_console.enable()
        colorama.init()
    except ImportError:
        G = Y = B = R = W = ''
else:
    G = '\033[92m'  # green
    H = '\033[97m'  # high
    B = '\033[94m'  # blue
    R = '\033[91m'  # red
    W = '\033[0m'   # white

# EXCEPTIONS
class EXCUTION_ERROR(Exception):
    pass


class RATE_LIMIT(Exception):
    pass


class PRIVATE_USER(Exception):
    pass


class FAILD_LOGIN(Exception):
    pass


class OUTPUT:
    def __init__(self):
        pass
    
    def Success(self, msg:str):
        return "{0}[+] {1}{2}".format(G, W, msg)

    def Error(self, msg:str):
        return "{0}[X] {1}{2}".format(R, W, msg)

    def Debug(self, msg:str):
        return "{0}[i] {1}{2}".format(B, W, msg)

    def High(self, msg:str):
        return " {0}{1}{2} ".format(H, msg, W) 
        
        


# REQUESTS HASHES
hashes = {
    "story": "45246d3fe16ccc6577e0bd297a5db1ab",
    "explore": "df0dcc250c2b18d9fd27c5581ef33c7c",
    "hash_tag": "ded47faa9a1aaded10161a2ff32abb6b",
    "profile_media": "42323d64886122307be10013ad2dcc44",
    "profile_follower": "37479f2b8209594dde7facb0d904896a",
    "profile_following": "58712303d941c6855d4e888c5f0cd22f",
    
    "psot_likes" : "e0f59e4a1c8d78d0161873bc2ee7ec44", #deactivated variables={"shortcode":"BrFwgDSg-Fs","include_reel":false,"first":50,"after":""}
    "post_comments" : "f0986789a5c5d17c2400faebf16efd0d", #deactivated variables={"shortcode":"BrFwgDSg-Fs","first":50,"after":""}
    "profile_tagged": "ff260833edf142911047af6024eb634a", #deactivated variables={"id":"2325314716","first":35,"after":""}
    "highlight_stort" : "f5193c25b1489ea38dffa35d6980ff8e" #variables={"reel_ids":[],"tag_names":[],"location_ids":[],"highlight_reel_ids":[""],"precomposed_overlay":false,"show_story_header_follow_button":true,"show_story_viewer_list":false,"story_viewer_first":0,"story_viewer_last":""}
}

# REQUESTS HEADERS
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive"
}
