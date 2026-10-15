function modelPredict(model, features) {
  if (!Array.isArray(features) || features.length !== model.feature_count || features.some(x=>!Number.isFinite(x))) throw new Error('Complete finite feature values are required.');
  let margin=Math.log(model.base/(1-model.base));
  for (const t of model.trees) {
    let node=0;
    while(t.left[node]!==-1){const v=Math.fround(features[t.feature[node]]);node=v<t.value[node]?t.left[node]:t.right[node];}
    margin+=t.value[node];
  }
  return 1/(1+Math.exp(-margin));
}
if(typeof module!=='undefined')module.exports=modelPredict;
