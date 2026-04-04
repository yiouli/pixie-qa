# ml-xsadd

<h3 align="center">
  
  <a href="https://www.zakodium.com">
   <img src="https://www.zakodium.com/brand/zakodium-logo-white.svg" width="50" alt="Zakodium logo" />
  </a>
  
  <p>
    Maintained by <a href="https://www.zakodium.com">Zakodium</a>
  </p>
  
  [![NPM version][npm-image]][npm-url]
  [![build status][ci-image]][ci-url]
  [![npm download][download-image]][download-url]
  
</h3>

JavaScript implementation of the XORSHIFT-ADD (XSadd) pseudo random number generator.

Based on the C code from https://github.com/MersenneTwister-Lab/XSadd.

## Installation

`$ npm install ml-xsadd`

## API

```js
const { XSadd } = require("ml-xsadd");

const gen = new XSadd();
const number = gen.getFloat();
```

### new XSadd([seed])

Creates a new XSadd instance. Seed is an optional integer that defaults to `Date.now()`.

### getUint32()

Returns a 32-bit integer r (0 <= r < 2^32).

### getFloat()

Returns a floating point number r (0.0 <= r < 1.0).

### random()

Like `getFloat()` but dynamically bound to the `XSadd` instance.  
You can use this function externally, like `Math.random`:

```js
const xsadd = new XSadd();
const random = xsadd.random;
const number = random();
```

### init(seed)

Reinitialize the generator with a new seed.

## LICENSE

[MIT](./LICENSE)

[npm-image]: https://img.shields.io/npm/v/ml-xsadd.svg?style=flat-square
[npm-url]: https://npmjs.org/package/ml-xsadd
[ci-image]: https://github.com/mljs/xsadd/workflows/Node.js%20CI/badge.svg?branch=main
[ci-url]: https://github.com/mljs/xsadd/actions?query=workflow%3A%22Node.js+CI%22
[download-image]: https://img.shields.io/npm/dm/ml-xsadd.svg?style=flat-square
[download-url]: https://npmjs.org/package/ml-xsadd
