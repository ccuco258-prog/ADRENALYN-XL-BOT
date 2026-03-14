import os
import json
import statistics
import time
import random
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

CARPETA_INVENTARIO = "Inventario"
ARCHIVO_INVENTARIO = os.path.join(CARPETA_INVENTARIO, "mi_coleccion.json")
ARCHIVO_EXCEL = os.path.join(CARPETA_INVENTARIO, "Inventario_Ebay_Adrenalyn.xlsx")

PALABRAS_PROHIBIDAS = [
    'lote', 'lotes', 'pack', 'set', 'caja', 'cajas', 'sobre', 'sobres', 
    'album', 'álbum', 'completa', 'completo', 'elegir', 'elige', 'faltas', 
    'desplegable', 'psa', 'pick', 'choose', 'binder', 'archivador'
]

def iniciar_navegador():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new') 
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument('--window-size=1920,1080')
    return uc.Chrome(options=options, version_main=145)

def limpiar_precio(texto):
    try:
        t = texto.upper().replace('EUR', '').replace('€', '').replace('A', '').strip()
        t = t.replace(',', '.')
        partes = t.split()
        if not partes: return None
        val = float(partes[0])
        return val if val > 0.10 else None
    except:
        return None

def buscar_en_ebay_profundo(driver, jugador, categoria, es_firmada):
    termino_firma = " firmada" if es_firmada else ""
    busqueda = f"Adrenalyn XL 2025 2026 {jugador} {categoria}{termino_firma}"
    url_busqueda = f"https://www.ebay.es/sch/i.html?_nkw={busqueda.replace(' ', '+')}&_sop=15"
    
    print(f"\n   [eBay] 🌐 Escaneando todos los anuncios encontrados...")
    driver.get(url_busqueda)
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    enlaces_validos = []
    
    # Palabra clave para verificar el nombre de forma más flexible
    primer_nombre = jugador.split()[0].lower()

    for a in soup.find_all('a', href=True):
        if '/itm/' in a['href']:
            titulo = a.text.lower()
            # Filtro flexible: comprueba que no sea lote y que contenga al menos el primer nombre
            if not any(palabra in titulo for palabra in PALABRAS_PROHIBIDAS) and primer_nombre in titulo:
                url_limpia = a['href'].split('?')[0] 
                enlaces_validos.append(url_limpia)
                
    enlaces_validos = list(set(enlaces_validos))
    precios_ebay = []
    
    if enlaces_validos:
        print(f"         ↳ Analizando {len(enlaces_validos)} enlaces...")
        for i, enlace in enumerate(enlaces_validos):
            print(f"         ↳ Procesando {i+1}/{len(enlaces_validos)}...", end="\r")
            driver.get(enlace)
            time.sleep(random.uniform(1.2, 2.0))
            item_soup = BeautifulSoup(driver.page_source, 'html.parser')
            precio_div = item_soup.select_one('.x-price-primary span.ux-textspans')
            if precio_div:
                p = limpiar_precio(precio_div.text)
                if p: precios_ebay.append(p)
    return precios_ebay

def buscar_en_todocoleccion(driver, jugador, categoria, es_firmada):
    termino_firma = " firmada" if es_firmada else ""
    busqueda = f"Adrenalyn XL 2025 2026 {jugador} {categoria}{termino_firma}"
    url_busqueda = f"https://www.todocoleccion.net/s/catalogo?t={busqueda.replace(' ', '+')}&orden=p"
    
    print(f"   [Todocoleccion] 🌐 Escaneando catálogo completo...")
    driver.get(url_busqueda)
    time.sleep(4)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    precios_tc = []
    primer_nombre = jugador.split()[0].lower()
    
    bloques = soup.select('.lote-card, .item, .lote')
    
    for b in bloques:
        try:
            titulo_el = b.select_one('.title, .lote-title, h2')
            if not titulo_el: continue
            titulo = titulo_el.text.lower()
            
            if primer_nombre in titulo and not any(p in titulo for p in PALABRAS_PROHIBIDAS):
                precio_el = b.select_one('.price, .lote-price, .m-0')
                if precio_el:
                    p = limpiar_precio(precio_el.text)
                    if p: precios_tc.append(p)
        except: continue
        
    print(f"   [Todocoleccion] 💰 Encontrados: {precios_tc}")
    return precios_tc

def buscar_y_guardar():
    print("\n" + "═"*50)
    print(" 🔎 BÚSQUEDA PROFUNDA (eBay + Todocoleccion)")
    print("═"*50)
    jugador = input(" 👤 Nombre del Jugador / Carta: ")
    categoria = input(" 🏆 Categoría: ")
    es_firmada = input(" ✍️ ¿Es una edición firmada? (s/n): ").lower() == 's'
    
    print("\n🚀 Iniciando motores (esto puede tardar al procesar todos los anuncios)...")
    driver = iniciar_navegador()
    
    try:
        precios_ebay = buscar_en_ebay_profundo(driver, jugador, categoria, es_firmada)
        precios_tc = buscar_en_todocoleccion(driver, jugador, categoria, es_firmada)
        
        todos = precios_ebay + precios_tc
        
        if todos:
            precio_final = round(statistics.median(todos), 2)
            print("\n" + "★"*50)
            print(f" 🎯 RESULTADO: {jugador.upper()}")
            print(f" 📊 Muestras: {len(todos)} precios analizados.")
            print(f" 💰 PRECIO MEDIO: {precio_final} €")
            print("★"*50)
            
            if input("\n💾 ¿Añadir al inventario? (s/n): ").lower() == 's':
                guardar_json(jugador, categoria, precio_final)
        else:
            print("\n❌ No se encontraron resultados. Intenta con términos menos específicos.")
            
    finally:
        driver.quit()

def guardar_json(jugador, categoria, precio):
    os.makedirs(CARPETA_INVENTARIO, exist_ok=True)
    coleccion = []
    if os.path.exists(ARCHIVO_INVENTARIO):
        with open(ARCHIVO_INVENTARIO, "r", encoding='utf-8') as f:
            coleccion = json.load(f)
    
    coleccion.append({
        "Jugador": jugador.title(),
        "Categoría": categoria.title(),
        "Precio Medio (€)": precio,
        "Fecha": str(date.today())
    })
    
    with open(ARCHIVO_INVENTARIO, "w", encoding='utf-8') as f:
        json.dump(coleccion, f, indent=4, ensure_ascii=False)
    print(" ✅ Guardado correctamente.")

def mostrar_inventario():
    print("\n" + "═"*50)
    print(" 🗃️  TU COLECCIÓN ADRENALYN 25-26")
    print("═"*50)
    if not os.path.exists(ARCHIVO_INVENTARIO):
        print(" ❌ El inventario está vacío.")
        return
    with open(ARCHIVO_INVENTARIO, "r", encoding='utf-8') as f:
        datos = json.load(f)
    if not datos: return
    total = sum(c['Precio Medio (€)'] for c in datos)
    for c in datos:
        print(f" ▪ {c['Jugador']:<15} | {c['Categoría']:<15} | {c['Precio Medio (€)']:>5} €")
    print("-" * 50)
    print(f" 💎 VALOR TOTAL: {round(total, 2)} €")
    print("═"*50)

def exportar_excel():
    if not os.path.exists(ARCHIVO_INVENTARIO): return
    df = pd.read_json(ARCHIVO_INVENTARIO)
    df.to_excel(ARCHIVO_EXCEL, index=False)
    print(f"\n ✨ Excel creado en: {ARCHIVO_EXCEL}")

def menu():
    while True:
        print("\n╔════════════════════════════════════════════════╗")
        print("║          🤖 ADRENALYN XL BOT TRACKER           ║")
        print("╚════════════════════════════════════════════════╝")
        print("  1. 🔍 Buscar carta (eBay + Todocoleccion)")
        print("  2. 📋 Ver mi Inventario")
        print("  3. 📊 Exportar a Excel")
        print("  4. 🚪 Salir")
        op = input("\n  👉 Opción: ")
        
        if op == '1': buscar_y_guardar()
        elif op == '2': mostrar_inventario()
        elif op == '3': exportar_excel()
        elif op == '4': break

if __name__ == "__main__":
    menu()