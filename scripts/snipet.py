# -*- coding: utf-8 -*-
from odbAccess import *
import visualization

def export_all_field_data(odb_path):
    # Открываем ODB файл только для чтения
    odb = openOdb(path=odb_path, readOnly=True)
    
    # Создаем файл для экспорта данных
    output_file = open('odb_export_log.txt', 'w')
    output_file.write("Field Export Log\n" + "="*30 + "\n")

    try:
        for step_name in odb.steps.keys():
            step = odb.steps[step_name]
            output_file.write("\nStep: %s\n" % step_name)
            
            for frame in step.frames:
                output_file.write("  Frame: %d (Value: %f)\n" % (frame.frameId, frame.frameValue))
                
                # Перебираем все доступные поля (S, LE, U, RF и т.д.)
                for field_name in frame.fieldOutputs.keys():
                    field = frame.fieldOutputs[field_name]
                    output_file.write("    Field: %s\n" % field_name)
                    
                    # 1. Экспорт КОРНЕВЫХ КОМПОНЕНТОВ (например, S11, S22, LE11)
                    if field.componentLabels:
                        output_file.write("      Components: %s\n" % str(field.componentLabels))
                        for label in field.componentLabels:
                            # Получаем подмножество данных для конкретного компонента
                            component_field = field.getSubset(componentLabel=label)
                            # Здесь можно итерироваться по component_field.values для получения чисел
                            output_file.write("        - Component %s extracted\n" % label)

                    # 2. Экспорт ИНВАРИАНТОВ (например, MISES, MAX_PRINCIPAL, TRESCA)
                    if field.validInvariants:
                        output_file.write("      Invariants: %s\n" % str(field.validInvariants))
                        for inv in field.validInvariants:
                            # Получаем скалярное поле для конкретного инварианта
                            try:
                                inv_field = field.getScalarField(invariant=inv)
                                output_file.write("        - Invariant %s extracted\n" % str(inv))
                            except:
                                output_file.write("        - Invariant %s failed (check data type)\n" % str(inv))

    finally:
        output_file.close()
        odb.close()
        print("Done. Check odb_export_log.txt")

# Пример вызова функции
# export_all_field_data('job_name.odb')