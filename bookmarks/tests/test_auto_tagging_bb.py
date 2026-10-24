from django.test import TestCase

from bookmarks.services import auto_tagging


class AutoTaggingBlackBoxTestCase(TestCase):

    def test_vl06_dominio_sem_fronteira_de_ponto_nao_deve_casar(self):
       
        script = "example.com dev"
        url = "https://notexample.com/"

       
        tags = auto_tagging.get_tags(script, url)

        self.assertEqual(tags, set())

    def test_vl09_padrao_com_barra_final_e_url_sem_barra_deve_casar(self):
    
        script = "example.com/ dev"
        url = "https://example.com"

      
        tags = auto_tagging.get_tags(script, url)


        self.assertEqual(tags, {"dev"})