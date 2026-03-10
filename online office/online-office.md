### 起服务

```
# 1. 创建目录 (推荐放在 /opt 下)
sudo mkdir -p /opt/onlyoffice/logs \
             /opt/onlyoffice/data \
             /opt/onlyoffice/lib \
             /opt/onlyoffice/db

# 2. 赋予权限 (确保 Docker 容器有权写入这些目录)
sudo chmod -R 777 /opt/onlyoffice

# 3. 运行容器 (注意修改了 -v 前半部分的路径)
docker run -i -t -d -p 62000:80 --restart=always \
  -v /opt/onlyoffice/logs:/var/log/onlyoffice \
  -v /opt/onlyoffice/data:/var/www/onlyoffice/Data \
  -v /opt/onlyoffice/lib:/var/lib/onlyoffice \
  -v /opt/onlyoffice/db:/var/lib/postgresql \
  -e JWT_ENABLED=false \
  onlyoffice/documentserver
```

127.0.0.1:62000



### 前端示例

```
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Document</title>
</head>
<body>

<!-- 注意：192.168.1.150:62000 ip+端口号 要改为实际服务映射到宿主机上的ip+端口号 -->
<script
        type="text/javascript"
        src="http://192.168.1.150:62000/web-apps/apps/api/documents/api.js"></script>
<button id="previewBtn">预览</button>
<!-- 这里的preview作为id标识,被下文中引用的DocsAPI.DocEditor('id标识',配置)所抓取 -->
<div id="preview"></div>
<script type="module">
    // 日志:查看服务是否链接正确
    console.log('DocsAPI:', DocsAPI);
    const previewBtn = document.getElementById('previewBtn');
    // 点击按钮监听
    previewBtn.addEventListener('click', () => {
        // 这里我们要预览office
        const config = {
            document: {
				// 补充1:文件类型
                fileType: 'xlsx', 
                // 预览文件名,可以不和实际文件名相同
                title: '111.xlsx',
                // 可读的公网文件链接
                // 或者是用在预览服务容器中的内部地址
                // 补充2:在用内部地址时容器需要开放访问权限
                url: 'http://192.168.1.150:62000/test.xlsx',
            },
            // 补充3:编辑权限
            editorConfig: {
                mode: 'edit',
            }, 
            // 补充4:编辑器类型,需要和文件类型对齐
            documentType: 'cell', 
            width: '100%', 
            height: '700px',
        };
        // 调用实现预览
        // 在id为preview的块元素中根据config的配置生成文件预览
        const docEditor = new DocsAPI.DocEditor('preview', config);
    });
</script>
</body>
</html>
```

### 补充1,4:编辑器类型： 文件类型

*文本类型*

 **word/text** : doc, docm, docx, dot, dotm, dotx, epub, fb2, fodt, htm, html, mht, mhtml, odt, ott, rtf, stw, sxw, txt, wps, wpt, xml

表格类型

**cell** :  csv, et, ett, fods, ods, ots, sxc, xls, xlsb, xlsm, xlsx, xlt, xltm, xltx, xml

*演示文稿类型*

**slide** :  dps, dpt, fodp, odp, otp, pot, potm, potx, pps, ppsm, ppsx, ppt, pptm, pptx, sxi

*类型为只读的文本编辑器（mode必须为 view ）*

**pdf** :djvu, docxf, oform, oxps, pdf, xps

### 补充2:如果用的是服务容器的内部地址，该容器需修改配置

    vim default.json
    将
    "request-filtering-agent": {
        "allowPrivateIPAddress": false,
        "allowMetaIPAddress": false
      },
    改为
    "request-filtering-agent": {
        "allowPrivateIPAddress": true,
        "allowMetaIPAddress": true
      }

### 补充3:编辑权限

view - 只读

edit - 读可写

fillForms - 可填写表单字段

