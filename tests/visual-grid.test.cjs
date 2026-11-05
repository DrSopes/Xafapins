const {test}=require('node:test');const assert=require('node:assert/strict');
const {grid}=require('../web/visual-grid.js');
test('viewport grid has nominal 250 m spacing without covering the country',()=>{
  const data=grid([1.99,41.99,2.02,42.02],42);
  const vertical=data.features.filter(f=>f.geometry.coordinates[0][0]===f.geometry.coordinates[1][0]);
  const spacing=(vertical[1].geometry.coordinates[0][0]-vertical[0].geometry.coordinates[0][0])*111320*Math.cos(42*Math.PI/180);
  assert.ok(Math.abs(spacing-250)<1e-6);
  assert.equal(grid([-18,27,5,44],40).features.length,0);
});
