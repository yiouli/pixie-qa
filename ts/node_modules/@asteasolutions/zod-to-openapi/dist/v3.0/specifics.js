"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OpenApiGeneratorV30Specifics = void 0;
class OpenApiGeneratorV30Specifics {
    get nullType() {
        return { nullable: true };
    }
    mapNullableOfArray(objects, isNullable) {
        if (isNullable) {
            return [...objects, this.nullType];
        }
        return objects;
    }
    mapNullableType(type, isNullable) {
        return Object.assign(Object.assign({}, (type ? { type } : undefined)), (isNullable ? this.nullType : undefined));
    }
    getNumberChecks(checks) {
        return Object.assign({}, ...checks.map(check => {
            switch (check.kind) {
                case 'min':
                    return check.inclusive
                        ? { minimum: Number(check.value) }
                        : { minimum: Number(check.value), exclusiveMinimum: true };
                case 'max':
                    return check.inclusive
                        ? { maximum: Number(check.value) }
                        : { maximum: Number(check.value), exclusiveMaximum: true };
                default:
                    return {};
            }
        }));
    }
}
exports.OpenApiGeneratorV30Specifics = OpenApiGeneratorV30Specifics;
