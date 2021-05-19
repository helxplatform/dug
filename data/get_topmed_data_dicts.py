output_dir = "/Users/awaldrop/Desktop/test/new_bdc_dbgap_data_dicts"
studies = [
#"phs000007.v29.p10",
#"phs000179.v5.p2",
#"phs000200.v11.p3",
#"phs000209.v13.p3",
#"phs000280.v3.p1",
#"phs000284.v1.p1",
"phs000285.v3.p2",
#"phs000286.v5.p1",
#"phs000287.v6.p1",
#"phs000289.v2.p1",
#"phs000741.v2.p1",
#"phs000810.v1.p1",
#"phs000914.v1.p1",
#"phs000956.v2.p1",
#"phs000988.v2.p1",
#"phs001013.v2.p2",
#"phs001238.v1.p1"
]

import os
from ftplib import FTP
for study_id in studies:

    study_variable = study_id.split('.')[0]
    print("Begin-------------------------")
    print(f"{study_id}")
    os.makedirs(f"{output_dir}/{study_id}")

    ftp = FTP('ftp.ncbi.nlm.nih.gov')
    ftp.login()

    # Step 1: First we try and get all the data_dict files
    ftp.cwd(f"/dbgap/studies/{study_variable}/{study_id}/pheno_variable_summaries")
    ftp_filelist = ftp.nlst(".")
    for ftp_filename in ftp_filelist:
        if 'data_dict' in ftp_filename:
            with open(f"{output_dir}/{study_id}/{ftp_filename}", "wb") as data_dict_file:
                    ftp.retrbinary(f"RETR {ftp_filename}", data_dict_file.write)

    # Step 2: Check to see if there's a GapExchange file in the parent folder
    #         and if there is, get it.
    ftp.cwd(f"/dbgap/studies/{study_variable}/{study_id}")
    ftp_filelist = ftp.nlst(".")
    for ftp_filename in ftp_filelist:
        if 'GapExchange' in ftp_filename:
            with open(f"{output_dir}/{study_id}/{ftp_filename}", "wb") as data_dict_file:
                ftp.retrbinary(f"RETR {ftp_filename}", data_dict_file.write)
    ftp.quit()
    print("End---------------------------")
