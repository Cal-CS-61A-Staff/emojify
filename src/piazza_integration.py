import re
from collections import namedtuple
from html import unescape

from auth import query
from integration import Integration

REGEX = "@([0-9]+)(_f([0-9]+))?"

Post = namedtuple("Post", ["subject", "content", "url", "full_cid"])


class PiazzaIntegration(Integration):
    def process(self):
        self.posts = []
        course = None
        for match in re.finditer(REGEX, self.message):
            full_cid = match.group(1) + (match.group(2) or "")
            cid = int(match.group(1))
            post = query("piazza/get_post", staff=True, cid=cid)
            course = course or query("piazza/course_id", staff=True)
            subject = post["history"][0]["subject"]
            content = post["history"][0]["content"]

            if match.group(3):
                fid = int(match.group(3))  # 1 indexed
                curr_id = 0
                for child in post["children"]:
                    if child["type"] != "followup":
                        continue
                    curr_id += 1
                    if fid == curr_id:
                        break
                else:
                    return
                content = child["subject"]

            content = unescape(re.sub("<[^<]+?>", "", content))
            url = "https://piazza.com/class/{}?cid={}".format(course, full_cid)

            self.posts.append(Post(subject, content, url, full_cid))

    @property
    def text(self):
        out = self.message
        for post in self.posts:
            out = out.replace("@{}".format(post.full_cid), "<{}|@{}>".format(post.url, post.full_cid))
        return out

    @property
    def attachments(self):
        return [
            {
                "color": "#3575a8",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":piazza: *<{}|{}>* \n {}".format(
                                post.url, post.subject, post.content[:2500]
                            ),
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open",
                            },
                            "value": "piazza_open_click",
                            "url": post.url,
                        },
                    },
                ]
            }
            for post in self.posts
        ]
