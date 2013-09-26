import re
import BeautifulSoup

BLOCKELS = (
    'address', 'article', 'aside', 'audio', 'blockquote', 'canvas', 'dd',
    'div', 'dl', 'fieldset', 'figcaption', 'figure', 'footer', 'form',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'noscript',
    'ol', 'p', 'pre', 'section', 'table', 'tfoot', 'ul', 'video')

FORMATTERS = {
    'p': lambda tag, content: '%s\n\n' % (content.strip(),),
    'li': lambda tag, content: '* %s\n' % (content.strip(),),
    'td': lambda tag, content: '%10s' % (content.strip(),),
#    'strong': lambda tag, content: '*%s*' % (content,),
#    'em': lambda tag, content: '_%s_' % (content,),
    'br': lambda tag, content: '\n',
    'a': lambda tag, content: (
        '%s (%s)' % (content.strip(), dict(tag.attrs)['href'])
        if dict(tag.attrs).get('href') else
        content.strip()),
#    'img': lambda tag, content: '(%s)' % (dict(tag.attrs)['src'],),
}

def html_to_text(html):
    soup = BeautifulSoup.BeautifulSoup(html)
    ret = []
    for tag in soup.contents:
        if isinstance(tag, basestring):
            ret.append(tag)
            continue
        name = tag.name.lower()
        formatter = FORMATTERS.get(name)
        if formatter is not None:
            ret.append(
                formatter(
                    tag,
                    html_to_text(u''.join(unicode(c) for c in tag.contents))))
        else:
            ret.append(
                html_to_text(u''.join(unicode(c) for c in tag.contents)))
            if name in BLOCKELS:
                ret.append('\n')
    return ''.join(ret)

def _get_sources(mediael):
    src = dict(mediael.attrs).get('src')
    if src:
        return [src]
    else:
        return [dict(tag.attrs)['src'] for tag in mediael.findAll('source')]

def urls_from_html(html):
    """ return a dict with urls

        the dict keys are the elemens from which the urls are retrieved (can
        be 'a', 'img', 'embed', 'iframe', 'audio' or 'video'), the values
        are lists of strings, except for 'audio' and 'video', where it's
        lists of lists of strings (since each audio or video tag can have
        multiple sources)
    """
    ret = {}
    soup = BeautifulSoup.BeautifulSoup(html)
    for tagname in ('a', 'img', 'embed', 'iframe', 'audio', 'video'):
        tags = soup.findAll(tagname)
        if tagname == 'a':
            value = [dict(tag.attrs)['href'] for tag in tags]
        elif tagname in ('audio', 'video'):
            value = [_get_sources(tag) for tag in tags]
        else:
            value = [dict(tag.attrs)['src'] for tag in tags]
        ret[tagname] = value
    return ret
