import { expectType, expectError } from 'tsd'
import { pdfImportService } from '../src/services/pdfImportService'
import type { SystemInfoResponse } from '../src/services/pdfImportService'
import useMessage from '../src/hooks/useMessage'

// pdfImportService SystemInfoResponse should have unknown summaries
const checkSystemInfoUnknown = async () => {
  const info: SystemInfoResponse = await pdfImportService.getSystemInfo()
  expectType<SystemInfoResponse>(info)
  if (info.extractor_summary) {
    // accessing unknown property should produce type errors when used unsafely
    // @ts-expect-error - unknown is not string
    expectError(info.extractor_summary.foo.toUpperCase())
  }
}

// useMessage open should accept MessageArgsProps
const { open, config } = useMessage()
// open should accept at least content with correct types
open({ content: 'ok' })
// invalid duration type should error
// @ts-expect-error - duration must be number
expectError(open({ content: 'ok', duration: 'fast' }))

// config should accept correct options
config({ maxCount: 3 })

// Dictionary service getSystemDictionaries returns typed list
import { UnifiedDictionaryService } from '../src/services/dictionary'
import type { SystemDictionary } from '../src/types/asset'

const dictSvc = new UnifiedDictionaryService()
const p = dictSvc.getSystemDictionaries('OWNERSHIP_STATUS')
expectType<Promise<SystemDictionary[]>>(p)