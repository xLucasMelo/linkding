from django.test import TestCase

from bookmarks.services import auto_tagging


class AutoTaggingWhiteBoxTestCase(TestCase):


    def test_wb01_padrao_sem_caminho_query_e_fragmento_casa_url_que_os_tem(self):
   
        script = "example.com dev"
        url = "https://example.com/page?a=b#intro"


        tags = auto_tagging.get_tags(script, url)


        self.assertEqual(tags, {"dev"})