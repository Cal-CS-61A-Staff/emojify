import re
from html import unescape

from auth import query
from integration import Integration


class PiazzaIntegration(Integration):
    def process(self):
        match = re.search("@([0-9]+)(_f([0-9]+))?", self.message)
        if match:
            full_cid = match.group(1) + (match.group(2) or "")
            cid = int(match.group(1))
            post = query("piazza/get_post", staff=True, cid=cid)
            course = query("piazza/course_id", staff=True)
            self.subject = post["history"][0]["subject"]
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

            self.content = unescape(re.sub("<[^<]+?>", "", content))
            self.url = "https://piazza.com/class/{}?cid={}".format(course, full_cid)

    @property
    def attachments(self):
        return [
            {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":piazza: *<{}|{}>* \n {}".format(
                                self.url, self.subject, self.content[:2500]
                            ),
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open",
                            },
                            "value": "piazza_open_click",
                            "url": self.url,
                        },
                    },
                ]
            }
        ]
