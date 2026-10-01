import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p = await PresentationFile.importPptx(await FileBlob.load('C:/Users/SuperUser/Downloads/django/presentacia/Ryazan-Arenda-Presentation-v4.pptx'));
console.log((await p.inspect({kind:'slide,textbox,shape,image,table,notes,layout',maxChars:30000})).ndjson);
