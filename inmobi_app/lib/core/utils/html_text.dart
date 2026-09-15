/// Convierte el HTML que guarda Odoo en texto legible para la app.
///
/// Odoo almacena las descripciones como HTML (`fields.Html`), con párrafos,
/// listas y negritas. Quitar todas las etiquetas a secas deja un bloque
/// corrido ilegible, así que aquí se respetan los saltos de bloque y las
/// viñetas, y se marcan los tramos en negrita para poder pintarlos.
library;

/// Un tramo de texto con su formato.
class HtmlRun {
  final String text;
  final bool bold;
  const HtmlRun(this.text, {this.bold = false});
}

class HtmlText {
  HtmlText._();

  // Marcas internas (zona de uso privado Unicode, no aparecen en texto real)
  // para no perder dónde empieza y acaba la negrita al barrer las etiquetas.
  static final _boldOpen = String.fromCharCode(0xE001);
  static final _boldClose = String.fromCharCode(0xE002);
  // Protege el espacio de la viñeta del recorte de espacios por línea.
  static final _bulletSpace = String.fromCharCode(0xE000);

  static const _entities = {
    '&nbsp;': ' ',
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&apos;': "'",
    '&#39;': "'",
    '&hellip;': '…',
    '&mdash;': '—',
    '&ndash;': '–',
    '&aacute;': 'á',
    '&eacute;': 'é',
    '&iacute;': 'í',
    '&oacute;': 'ó',
    '&uacute;': 'ú',
    '&ntilde;': 'ñ',
    '&Ntilde;': 'Ñ',
    '&uuml;': 'ü',
  };

  /// Texto plano ya ordenado: saltos de línea, párrafos y viñetas.
  static String toPlain(String html) => toRuns(html).map((r) => r.text).join();

  /// El mismo texto partido en tramos, indicando cuáles van en negrita.
  static List<HtmlRun> toRuns(String html) {
    if (html.trim().isEmpty) return const [];

    var s = html;

    // Saltos de bloque.
    s = s.replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n');
    s = s.replaceAll(
      RegExp(r'</(p|div|h[1-6]|tr|blockquote)\s*>', caseSensitive: false),
      '\n\n',
    );

    // Listas: cada elemento con su viñeta.
    s = s.replaceAll(
      RegExp(r'<li[^>]*>', caseSensitive: false),
      '\n•$_bulletSpace',
    );
    // El cierre no aporta salto: lo pone el <li> siguiente o el </ul>.
    // Si no, la lista salía con una línea en blanco entre cada viñeta.
    s = s.replaceAll(RegExp(r'</li\s*>', caseSensitive: false), '');
    s = s.replaceAll(RegExp(r'</(ul|ol)\s*>', caseSensitive: false), '\n');

    // Negritas: se marcan antes de barrer el resto de etiquetas.
    s = s.replaceAll(
      RegExp(r'<(b|strong)(\s[^>]*)?>', caseSensitive: false),
      _boldOpen,
    );
    s = s.replaceAll(
      RegExp(r'</(b|strong)\s*>', caseSensitive: false),
      _boldClose,
    );

    s = s.replaceAll(RegExp(r'<[^>]*>'), '');

    _entities.forEach((entidad, valor) {
      s = s.replaceAll(entidad, valor);
    });
    // Entidades numéricas sueltas (&#8220; y similares).
    s = s.replaceAllMapped(RegExp(r'&#(\d+);'), (m) {
      final codigo = int.tryParse(m.group(1)!);
      return codigo == null ? m.group(0)! : String.fromCharCode(codigo);
    });

    // Espacios repetidos dentro de cada línea, sin tocar los saltos.
    s = s
        .split('\n')
        .map((l) => l.replaceAll(RegExp(r'[ \t ]+'), ' ').trim())
        .join('\n');
    s = s.replaceAll(_bulletSpace, ' ');
    s = s.replaceAll(RegExp(r'\n{3,}'), '\n\n');
    // Lista compacta: el HTML trae saltos entre <li> que, sumados al de la
    // propia viñeta, dejaban una línea en blanco entre cada una.
    s = s.replaceAll(RegExp(r'\n{2,}(?=\u2022 )'), '\n');
    s = s.trim();

    return _partir(s);
  }

  static List<HtmlRun> _partir(String s) {
    final runs = <HtmlRun>[];
    final buffer = StringBuffer();
    var negritas = 0;

    void volcar() {
      if (buffer.isEmpty) return;
      runs.add(HtmlRun(buffer.toString(), bold: negritas > 0));
      buffer.clear();
    }

    for (var i = 0; i < s.length; i++) {
      final c = s[i];
      if (c == _boldOpen) {
        volcar();
        negritas++;
      } else if (c == _boldClose) {
        volcar();
        if (negritas > 0) negritas--;
      } else {
        buffer.write(c);
      }
    }
    volcar();
    return runs;
  }
}
