const form = document.getElementById("form");
const overlay = document.getElementById("overlay");
const error = document.getElementById("error");

form.onsubmit = async e=>{
 e.preventDefault()

 const file = document.getElementById("file").files[0]
 if(!file){ alert("画像を選択してください"); return }

 overlay.classList.remove("hidden")
 error.textContent = ""

 const fd = new FormData()
 fd.append("image", file)
 fd.append("name", document.getElementById("name").value)
 fd.append("address", document.getElementById("address").value)
 fd.append("doc_type", document.querySelector('input[name="doc_type"]:checked').value)

 try{
  const res = await fetch("/process",{method:"POST",body:fd})

  if(res.ok){
    const blob = await res.blob()
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = "translated.pdf"
    a.click()
  }else{
    let msg="エラー"
    try{
      const d = await res.json()
      msg=d.error
    }catch{}

    if(res.status===503) msg="現在アクセスが集中しています。少し待って再度お試しください"
    error.textContent=msg
  }

 }catch{
  error.textContent="通信エラー"
 }

 overlay.classList.add("hidden")
}