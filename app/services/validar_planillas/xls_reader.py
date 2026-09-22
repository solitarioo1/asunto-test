import xlrd


def abrir_libro(datos: bytes) -> xlrd.book.Book:
    # ignore_workbook_corruption: algunos sistemas (seguros/gobierno) generan .xls
    # con una cadena de sectores OLE2 ligeramente no conforme al spec; Excel los
    # abre igual, pero xlrd por defecto los rechaza con CompDocError.
    return xlrd.open_workbook(file_contents=datos, ignore_workbook_corruption=True)


def hoja_por_nombre(libro: xlrd.book.Book, nombre: str) -> xlrd.sheet.Sheet:
    try:
        return libro.sheet_by_name(nombre)
    except xlrd.XLRDError:
        pass
    for nombre_hoja in libro.sheet_names():
        if nombre_hoja.strip().lower() == nombre.strip().lower():
            return libro.sheet_by_name(nombre_hoja)
    raise xlrd.XLRDError(f"no se encontró la hoja '{nombre}' (hojas disponibles: {libro.sheet_names()})")
