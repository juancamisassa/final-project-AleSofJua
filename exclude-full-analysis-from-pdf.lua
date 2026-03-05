-- Exclude "Full Analysis" section and everything after it when rendering to PDF
function Pandoc(doc)
  if quarto.doc.is_format("pdf") then
    local blocks = doc.blocks
    local new_blocks = {}
    for i, block in ipairs(blocks) do
      if block.t == "Header" and block.level == 2 then
        local text = pandoc.utils.stringify(block.content)
        if text:match("Full Analysis") then
          break  -- Stop: don't include this heading or anything after
        end
      end
      table.insert(new_blocks, block)
    end
    return pandoc.Pandoc(new_blocks, doc.meta)
  end
  return doc
end
