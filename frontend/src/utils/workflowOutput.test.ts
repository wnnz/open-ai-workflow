import { describe, expect, it } from 'vitest'
import { collectWorkflowFiles, collectWorkflowImages, compactWorkflowOutput } from './workflowOutput'

describe('workflow image outputs', () => {
  it('collects data and remote image results without treating arbitrary URLs as images', () => {
    const output = {
      images: ['data:image/webp;base64,AAAA', 'https://cdn.example.com/result/1'],
      callback_url: 'https://example.com/callback',
    }
    expect(collectWorkflowImages(output)).toEqual(output.images)
  })

  it('compacts base64 image data for JSON display', () => {
    expect(compactWorkflowOutput({ images: ['data:image/png;base64,AAAA'] })).toEqual({
      images: ['[image/png image data, 0.0 KB]'],
    })
  })

  it('collects downloadable workflow files once', () => {
    const file = {
      id: 'file-1',
      filename: 'exam-answered.docx',
      content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      size: 2048,
      download_url: '/v1/apps/exam/runs/run-1/files/file-1',
    }
    expect(collectWorkflowFiles({ file, nested: [file] })).toEqual([file])
  })
})
