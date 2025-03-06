from bs4 import BeautifulSoup
import html2text
import re

def clean_html_to_markdown(htmlContent):
    soup = BeautifulSoup(htmlContent, 'html.parser')
    for element in soup(['script', 'style', 'link', 'meta', 'img']):
        element.decompose()
    
    for element in soup.find_all(True):
        if 'style' in element.attrs:
            del element['style']
        if 'class' in element.attrs:
            del element['class']
    
    for element in soup(['footer', 'nav']):
        element.decompose()

    html_str = str(soup)
    
    h = html2text.HTML2Text()
    h.ignore_links = False 
    h.ignore_images = True 
    h.ignore_emphasis = False 
    h.body_width = 0 
    
    markdown = h.handle(html_str)
    markdown = re.sub(r'\n\s*\n', '\n\n', markdown)
    markdown = markdown.strip()
    markdown = re.sub(r'(__+|_+)', '', markdown)

    return markdown

def main():
    with open('aa.html', 'r', encoding='utf-8') as file:
        htmlContent = file.read()
    markdown_content = clean_html_to_markdown(htmlContent)
    with open('output.md', 'w', encoding='utf-8') as file:
        file.write(markdown_content)
    
    print("Conversion complete! Check output.md for the results.")

if __name__ == "__main__":
    main()
