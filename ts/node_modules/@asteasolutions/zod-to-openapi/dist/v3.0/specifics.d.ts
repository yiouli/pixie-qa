import type { ReferenceObject, SchemaObject } from 'openapi3-ts/oas30';
import { OpenApiVersionSpecifics } from '../openapi-generator';
import { ZodNumericCheck } from '../types';
export declare class OpenApiGeneratorV30Specifics implements OpenApiVersionSpecifics {
    get nullType(): {
        nullable: boolean;
    };
    mapNullableOfArray(objects: (SchemaObject | ReferenceObject)[], isNullable: boolean): (SchemaObject | ReferenceObject)[];
    mapNullableType(type: NonNullable<SchemaObject['type']> | undefined, isNullable: boolean): Pick<SchemaObject, 'type' | 'nullable'>;
    getNumberChecks(checks: ZodNumericCheck[]): Pick<SchemaObject, 'minimum' | 'exclusiveMinimum' | 'maximum' | 'exclusiveMaximum'>;
}
