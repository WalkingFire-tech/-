"""
Scrapling风格的搜索引擎适配器
使用curl_cffi的TLS指纹伪装替代requests，解决DDG TLS错误

搜索引擎优先级：
1. 百度（中文查询最优，TLS指纹伪装稳定）
2. Bing（英文查询备选）
3. DDG（降级备选，网络环境可能不可用）
"""

import re
import time
from typing import List, Dict, Optional
from urllib.parse import quote

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_CURL_CFFI_AVAILABLE = False
try:
    from curl_cffi.requests import Session as CurlSession
    _CURL_CFFI_AVAILABLE = True
except ImportError:
    logger.warning("curl_cffi未安装，搜索将使用requests降级")


def _create_stealth_session():
    if not _CURL_CFFI_AVAILABLE:
        return None
    return CurlSession(impersonate="chrome120")


def search_baidu(query: str, max_results: int = 8, timeout: int = 15) -> List[Dict]:
    if not _CURL_CFFI_AVAILABLE:
        return []

    try:
        session = _create_stealth_session()
        encoded_q = quote(query)
        url = f"https://www.baidu.com/s?wd={encoded_q}"
        r = session.get(url, timeout=timeout)

        if r.status_code != 200:
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('div', class_='result')
        if not results:
            results = soup.find_all('div', class_='c-container')

        parsed = []
        for item in results[:max_results]:
            title_el = item.find('h3')
            if not title_el:
                continue

            title = title_el.get_text().strip()
            if not title or len(title) < 4:
                continue

            snippet = ""
            for cls in ['content-right_8Zs40', 'c-abstract']:
                snippet_el = item.find('span', class_=cls) or item.find('div', class_=cls)
                if snippet_el:
                    snippet = snippet_el.get_text().strip()
                    break
            if not snippet:
                snippet_el = item.find('p')
                if snippet_el:
                    snippet = snippet_el.get_text().strip()

            link_el = item.find('a')
            link = link_el.get('href', '') if link_el else ''

            parsed.append({
                "title": title[:100],
                "snippet": snippet[:300],
                "link": link,
                "source": "baidu"
            })

        logger.info(f"🔍 百度搜索: '{query[:30]}' → {len(parsed)}条结果")
        return parsed

    except Exception as e:
        logger.debug(f"百度搜索失败: {e}")
        return []


def search_bing(query: str, max_results: int = 8, timeout: int = 15) -> List[Dict]:
    if not _CURL_CFFI_AVAILABLE:
        return []

    try:
        session = _create_stealth_session()
        encoded_q = quote(query)
        url = f"https://www.bing.com/search?q={encoded_q}&setlang=zh-Hans"
        r = session.get(url, timeout=timeout)

        if r.status_code != 200:
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('li', class_='b_algo')

        parsed = []
        for item in results[:max_results]:
            title_el = item.find('h2')
            if not title_el:
                continue

            title = title_el.get_text().strip()
            if not title or len(title) < 4:
                continue

            snippet_el = item.find('p')
            snippet = snippet_el.get_text().strip() if snippet_el else ""

            link_el = item.find('a')
            link = link_el.get('href', '') if link_el else ''

            parsed.append({
                "title": title[:100],
                "snippet": snippet[:300],
                "link": link,
                "source": "bing"
            })

        logger.info(f"🔍 Bing搜索: '{query[:30]}' → {len(parsed)}条结果")
        return parsed

    except Exception as e:
        logger.debug(f"Bing搜索失败: {e}")
        return []


def search_web_stealthy(query: str, max_results: int = 8, timeout: int = 15) -> List[Dict]:
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))

    if has_chinese:
        results = search_baidu(query, max_results, timeout)
        if results:
            return results
        results = search_bing(query, max_results, timeout)
        if results:
            return results
    else:
        results = search_bing(query, max_results, timeout)
        if results:
            return results
        results = search_baidu(query, max_results, timeout)
        if results:
            return results

    return []