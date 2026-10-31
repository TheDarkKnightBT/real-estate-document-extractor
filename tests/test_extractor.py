"""Tests añadidos posteriormente para el portafolio; sin servicios remotos."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import main


class ExtractorTests(unittest.TestCase):
    def test_csv_injection(self):
        for text in ('=1+1', '  +cmd', '\t@SUM(A1)', '-2'):
            self.assertEqual(main.proteger_celda(text), "'"+text)
        self.assertEqual(main.proteger_celda('USD 120000'), 'USD 120000')
        self.assertIsNone(main.proteger_celda(None))

    def test_missing_configuration(self):
        with patch.object(main,'AZURE_KEY','TU_CLAVE_AZURE'):
            with self.assertRaises(ValueError): main.revisar_configuracion()

    def test_empty_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'empty.pdf'
            path.touch()
            with self.assertRaises(ValueError): main.revisar_pdf(path)

    def test_f0_rejects_more_than_two_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'demo.pdf'
            path.write_bytes(b'%PDF-demo')
            reader=SimpleNamespace(is_encrypted=False,pages=[1,2,3])
            with patch.object(main,'PdfReader',return_value=reader), patch.object(main,'NIVEL_AZURE','F0'):
                with self.assertRaises(ValueError): main.revisar_pdf(path)

    def client(self, data):
        client=Mock()
        client.responses.create.return_value=SimpleNamespace(status='completed',output=[],output_text=json.dumps(data),model='mock',usage=None)
        return client

    def fields(self):
        return {**{k:None for k in main.CAMPOS},'varias_propiedades':False,'observaciones':'','evidencia':''}

    def test_invalid_json_shape(self):
        with self.assertRaises(ValueError): main.extraer_campos(self.client({'precio':'1'}),'demo')

    def test_invalid_json_types(self):
        data=self.fields()
        data['precio']=100
        with self.assertRaises(ValueError): main.extraer_campos(self.client(data),'demo')

    def test_multiple_properties_clears_fields(self):
        data=self.fields()
        data.update(precio='100',varias_propiedades=True)
        result,_=main.extraer_campos(self.client(data),'demo')
        self.assertTrue(all(result[k] is None for k in main.CAMPOS))

    def test_followup_cannot_send_key_to_different_host(self):
        session=Mock()
        session.post.return_value=SimpleNamespace(status_code=202,headers={'Operation-Location':'https://example.invalid/result'})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'demo.pdf'
            path.write_bytes(b'%PDF-demo')
            with patch.object(main,'AZURE_ENDPOINT','https://resource.cognitiveservices.azure.com'):
                with self.assertRaises(RuntimeError): main.leer_pdf(session,path,1)
        session.get.assert_not_called()


if __name__=='__main__': unittest.main()
