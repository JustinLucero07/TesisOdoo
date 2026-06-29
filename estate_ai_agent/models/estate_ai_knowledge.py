# -*- coding: utf-8 -*-
"""Base de conocimiento (RAG) del agente IA.

Indexa documentación estática (manuales, guías, READMEs de los módulos) como
fragmentos con su embedding, y permite recuperar los más relevantes para una
consulta. Los vectores se guardan como JSON y la similitud (coseno) se calcula
en Python con numpy — no requiere pgvector ni servicios externos.
"""
import glob
import json
import logging
import os

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

EMBED_MODEL_OPENAI = 'text-embedding-3-small'
# Candidatos de modelo de embeddings de Gemini (varían según versión de API/clave);
# se prueba en orden hasta que uno responda.
EMBED_MODELS_GEMINI = ('gemini-embedding-001', 'text-embedding-004', 'models/text-embedding-004')
CHUNK_SIZE = 1200      # caracteres por fragmento
CHUNK_OVERLAP = 200    # solapamiento entre fragmentos

# Manuales propios del módulo (se despliegan junto al código).
_KNOWLEDGE_GLOB = 'data/knowledge/*.md'
# READMEs de los módulos del proyecto (también se despliegan).
_README_MODULES = [
    'estate_management', 'estate_crm', 'estate_ai_agent',
    'estate_social', 'estate_wordpress',
]


class EstateAIKnowledge(models.Model):
    _name = 'estate.ai.knowledge'
    _description = 'Base de conocimiento del agente IA (RAG)'
    _order = 'source, chunk_index'

    name = fields.Char(string='Título', required=True)
    source = fields.Char(string='Fuente', index=True,
                         help='Documento de origen del fragmento.')
    chunk_index = fields.Integer(string='Fragmento', default=0)
    content = fields.Text(string='Contenido', required=True)
    embedding = fields.Text(string='Embedding (JSON)')
    active = fields.Boolean(default=True)

    # ── Embeddings ───────────────────────────────────────────────────────────
    @api.model
    def _embed_provider(self):
        """Devuelve (proveedor, api_key) para generar embeddings."""
        ICP = self.env['ir.config_parameter'].sudo()
        active = ICP.get_param('estate_ai.provider', 'chatgpt')
        legacy = ICP.get_param('estate_ai.api_key', '') or ''
        okey = ICP.get_param('estate_ai.openai_api_key', '') or (legacy if active == 'chatgpt' else '')
        gkey = ICP.get_param('estate_ai.gemini_api_key', '') or (legacy if active == 'gemini' else '')
        # Se prioriza el proveedor activo; si no tiene clave, se usa el otro.
        if active == 'gemini' and gkey:
            return ('gemini', gkey)
        if active == 'chatgpt' and okey:
            return ('openai', okey)
        if okey:
            return ('openai', okey)
        if gkey:
            return ('gemini', gkey)
        return (None, None)

    @api.model
    def _provider_keys(self):
        """Devuelve {'openai': key, 'gemini': key} con las claves configuradas."""
        ICP = self.env['ir.config_parameter'].sudo()
        active = ICP.get_param('estate_ai.provider', 'chatgpt')
        legacy = ICP.get_param('estate_ai.api_key', '') or ''
        return {
            'openai': ICP.get_param('estate_ai.openai_api_key', '') or (legacy if active == 'chatgpt' else ''),
            'gemini': ICP.get_param('estate_ai.gemini_api_key', '') or (legacy if active == 'gemini' else ''),
        }

    @api.model
    def _embed_with(self, provider, key, texts):
        """Genera embeddings con un proveedor concreto."""
        if provider == 'openai':
            import openai
            client = openai.OpenAI(api_key=key)
            resp = client.embeddings.create(model=EMBED_MODEL_OPENAI, input=texts)
            return [d.embedding for d in resp.data]
        # Gemini con el SDK nuevo (google-genai), el mismo que usa el chat.
        from google import genai
        client = genai.Client(api_key=key)
        last = None
        for mdl in EMBED_MODELS_GEMINI:
            try:
                resp = client.models.embed_content(model=mdl, contents=texts)
                return [list(e.values) for e in resp.embeddings]
            except Exception as e:
                last = e
        raise last

    @api.model
    def _embed_texts(self, texts):
        """Genera embeddings probando el proveedor activo y, si falla, el otro."""
        provider, _key = self._embed_provider()
        if not provider:
            raise UserError('Configure una API Key (OpenAI o Gemini) en Ajustes → Agente IA '
                            'para generar la base de conocimiento.')
        keys = self._provider_keys()
        order = [provider] + [p for p in ('openai', 'gemini') if p != provider]
        errors = []
        for p in order:
            k = keys.get(p)
            if not k:
                continue
            try:
                return self._embed_with(p, k, texts)
            except Exception as e:
                errors.append('%s: %s' % (p, e))
                _logger.warning('Embeddings con %s fallaron: %s', p, e)
        raise UserError('No se pudieron generar los embeddings. Revisa las API Keys y que las '
                        'librerías estén instaladas. Detalle: ' + ' | '.join(errors))

    # ── Troceado ─────────────────────────────────────────────────────────────
    @staticmethod
    def _chunk_text(text):
        """Divide un texto largo en fragmentos con solapamiento."""
        text = (text or '').strip()
        if not text:
            return []
        chunks = []
        start = 0
        n = len(text)
        while start < n:
            end = min(start + CHUNK_SIZE, n)
            chunks.append(text[start:end].strip())
            if end >= n:
                break
            start = end - CHUNK_OVERLAP
        return [c for c in chunks if c]

    # ── Indexación ─────────────────────────────────────────────────────────--
    @api.model
    def _gather_documents(self):
        """Devuelve [(titulo, fuente, texto)] de manuales del módulo y READMEs."""
        from odoo.modules.module import get_module_path
        docs = []
        mod_path = get_module_path('estate_ai_agent')
        for path in sorted(glob.glob(os.path.join(mod_path, _KNOWLEDGE_GLOB))):
            try:
                with open(path, encoding='utf-8') as f:
                    docs.append((os.path.basename(path), os.path.basename(path), f.read()))
            except Exception as e:
                _logger.warning('No se pudo leer %s: %s', path, e)
        for mod in _README_MODULES:
            mp = get_module_path(mod)
            if not mp:
                continue
            readme = os.path.join(mp, 'README.md')
            if os.path.exists(readme):
                try:
                    with open(readme, encoding='utf-8') as f:
                        docs.append(('README %s' % mod, 'README/%s' % mod, f.read()))
                except Exception as e:
                    _logger.warning('No se pudo leer %s: %s', readme, e)
        return docs

    @api.model
    def action_reindex_knowledge(self):
        """Reconstruye la base de conocimiento: trocea, embebe y guarda."""
        docs = self._gather_documents()
        if not docs:
            raise UserError('No se encontró documentación para indexar.')
        # Preparar fragmentos
        rows = []  # (name, source, idx, content)
        for title, source, text in docs:
            for i, chunk in enumerate(self._chunk_text(text)):
                rows.append((title, source, i, chunk))
        if not rows:
            raise UserError('La documentación no produjo fragmentos indexables.')

        # Embeddings por lotes (para no exceder límites del proveedor)
        contents = [r[3] for r in rows]
        embeddings = []
        batch = 64
        for k in range(0, len(contents), batch):
            embeddings.extend(self._embed_texts(contents[k:k + batch]))

        # Reemplazar el índice anterior
        self.sudo().search([]).unlink()
        vals = [{
            'name': rows[j][0],
            'source': rows[j][1],
            'chunk_index': rows[j][2],
            'content': rows[j][3],
            'embedding': json.dumps(embeddings[j]),
        } for j in range(len(rows))]
        self.sudo().create(vals)
        _logger.info('Base de conocimiento reindexada: %d fragmentos de %d documentos.',
                     len(vals), len(docs))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Conocimiento reindexado',
                'message': '%d fragmentos indexados de %d documentos.' % (len(vals), len(docs)),
                'type': 'success',
            },
        }

    # ── Búsqueda (RAG) ─────────────────────────────────────────────────────--
    @api.model
    def search_knowledge(self, query, top_k=4):
        """Devuelve los fragmentos más relevantes para la consulta.

        Retorna una lista de dicts {source, content, score}.
        """
        import numpy as np
        records = self.sudo().search([])
        if not records:
            return []
        try:
            q_vec = np.array(self._embed_texts([query])[0], dtype='float32')
        except Exception as e:
            _logger.warning('No se pudo embeber la consulta RAG: %s', e)
            return []
        q_norm = np.linalg.norm(q_vec) or 1.0

        scored = []
        for rec in records:
            if not rec.embedding:
                continue
            try:
                vec = np.array(json.loads(rec.embedding), dtype='float32')
            except Exception:
                continue
            if vec.shape != q_vec.shape:
                continue  # embeddings de otro proveedor/dimensión
            sim = float(np.dot(q_vec, vec) / (q_norm * (np.linalg.norm(vec) or 1.0)))
            scored.append((sim, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{
            'source': rec.source,
            'content': rec.content,
            'score': round(sim, 3),
        } for sim, rec in scored[:top_k]]
