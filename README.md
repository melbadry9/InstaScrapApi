## Install
- `pip install InstaScrapApi`


## Usage
- Class USER
```python
from InstaScrapApi import USER

user1 = USER("username", cookies=None, session=None, proxy={}, ssl=True, verbose=False, bar=True, threads=5)
user1.LogIn(username="", password="")

#must be called
user1.Information()

#get_number set to 0 will scrap all 
user1.Story()
user1.Media(get_number=0, per_request=50, after="")
user1.Follower(get_number=50, per_request=15, after="")
user1.Following(get_number=100, per_request=50, after="")

```
- Class ROOT
```python
from InstaScrapApi import ROOT

root1 = ROOT("username", cookies=None, session=None, proxy={}, ssl=True, verbose=False, bar=True, threads=5)
root1.LogIn(username="", password="")

#must be called
root1.Information()

#get_number set to 0 will scrap all 
root1.Story()
root1.Notifcation()
root1.Search(query="")
root1.HashTag(tag="", get_number=50, after="")
root1.Media(get_number=0, per_request=50, after="")
root1.Follower(get_number=50, per_request=15, after="")
root1.Following(get_number=100, per_request=50, after="")

#get_number set to 0 will scrap nothing
#after is string of integer ex: "3"
root1.ExploreMedia(get_number=14, per_request=14, after="1")

```
